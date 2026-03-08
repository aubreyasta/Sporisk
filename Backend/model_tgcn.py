"""
SporeRisk - T-GCN: Temporal Graph Convolutional Network
=========================================================
Combines GNN (spatial: county-to-county influence) with
LSTM (temporal: multi-month memory) for Valley Fever prediction.

TWO IMPLEMENTATIONS:
  1. Pure NumPy (runs anywhere, including this container)
  2. PyTorch + PyG (uncomment at bottom — run on your own machines)

Run:  python model_tgcn.py
Input:  sporerisk_master.csv
Output: tgcn_predictions.csv, prints evaluation metrics

Architecture:
  Input → GCN Layer → LSTM Cell → Dense → Sigmoid → Risk Score
"""

import os
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import warnings
warnings.filterwarnings("ignore")


# ============================================================
# GRAPH DEFINITION: Central Valley County Adjacency
# ============================================================
# This is the "graph" part of the GNN. Each county is a node,
# and edges connect counties that share a border.
# The GNN lets neighboring counties influence each other's
# predictions — so a dust storm in Kern affects Tulare's risk.

COUNTIES = ["Fresno", "Kern", "Kings", "Madera", 
            "Merced", "San Joaquin", "Stanislaus", "Tulare"]

# County index mapping
C2I = {c: i for i, c in enumerate(COUNTIES)}

# Adjacency list: which counties border each other?
# (based on actual California county borders)
EDGES = [
    ("Fresno", "Kings"),      ("Fresno", "Tulare"),
    ("Fresno", "Madera"),     ("Fresno", "Merced"),
    ("Kern", "Kings"),        ("Kern", "Tulare"),
    ("Kings", "Tulare"),      ("Madera", "Merced"),
    ("Merced", "Stanislaus"), ("Merced", "San Joaquin"),
    ("San Joaquin", "Stanislaus"),
]

def build_adjacency_matrix():
    """
    Builds the normalized adjacency matrix A_hat for the GCN.
    
    In plain English: this matrix tells the GNN "when updating
    Fresno's features, also look at Kings, Tulare, Madera, and
    Merced's features because they're neighbors."
    
    The normalization (D^-0.5 * A * D^-0.5) ensures that counties
    with more neighbors don't get disproportionately large signals.
    """
    N = len(COUNTIES)
    A = np.eye(N)  # self-loops (each county connects to itself)
    
    for c1, c2 in EDGES:
        i, j = C2I[c1], C2I[c2]
        A[i, j] = 1.0
        A[j, i] = 1.0  # undirected graph
    
    # Symmetric normalization: D^(-1/2) * A * D^(-1/2)
    D = np.diag(A.sum(axis=1))           # degree matrix
    D_inv_sqrt = np.diag(1.0 / np.sqrt(A.sum(axis=1)))  # D^(-1/2)
    A_hat = D_inv_sqrt @ A @ D_inv_sqrt  # normalized adjacency
    
    print(f"  Graph: {N} nodes, {len(EDGES)} edges")
    print(f"  Adjacency matrix shape: {A_hat.shape}")
    
    return A_hat


# ============================================================
# DATA PREPARATION
# ============================================================

def prepare_sequences(csv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "sporerisk_master_corrected.csv"), window=6):
    """
    Converts the daily CSV into monthly sequences for the T-GCN.
    
    Output shape per sample:
      X: (window, num_counties, num_features)  →  e.g. (6, 8, 6)
      y: (num_counties,)                       →  e.g. (8,)
    
    Think of it as: "Given the last 6 months of weather data
    for ALL 8 counties simultaneously, predict next month's
    cases for ALL 8 counties."
    """
    print("Preparing sequences...")
    
    # Load and aggregate to monthly (same as baseline)
    df = pd.read_csv(csv_path)
    df["date"] = pd.to_datetime(df["date"])
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    
    monthly = df.groupby(["county", "year", "month"]).agg({
        "precip_mm":          "sum",
        "soil_moisture_m3m3": "mean",
        "wind_speed_kmh":     "mean",
        "pm10_ugm3":          "mean",
        "tmax_approx_c":      "mean",
        "case_count":         "first",
    }).reset_index()
    
    # Seasonal case distribution (same curve as baseline)
    SEASONAL = {1:.04, 2:.03, 3:.04, 4:.05, 5:.06, 6:.07,
                7:.08, 8:.12, 9:.14, 10:.15, 11:.13, 12:.09}
    monthly["monthly_cases"] = monthly.apply(
        lambda r: r["case_count"] * SEASONAL[r["month"]], axis=1
    )
    
    # Features to use (the T-GCN learns lags on its own!)
    feature_cols = ["precip_mm", "soil_moisture_m3m3", "wind_speed_kmh",
                    "pm10_ugm3", "tmax_approx_c"]
    
    # --- Build the 3D tensor: (time, counties, features) ---
    # Sort by time
    monthly = monthly.sort_values(["year", "month", "county"])
    
    # Get unique time periods
    time_periods = monthly.groupby(["year", "month"]).ngroups
    
    # Reshape into (time, 8 counties, 5 features)
    n_counties = len(COUNTIES)
    n_features = len(feature_cols)
    
    X_tensor = np.zeros((time_periods, n_counties, n_features))
    y_tensor = np.zeros((time_periods, n_counties))
    
    for t, ((year, month), group) in enumerate(monthly.groupby(["year", "month"])):
        for _, row in group.iterrows():
            ci = C2I.get(row["county"])
            if ci is not None:
                X_tensor[t, ci] = row[feature_cols].values
                y_tensor[t, ci] = row["monthly_cases"]
    
    print(f"  Tensor shape: ({time_periods} months, {n_counties} counties, {n_features} features)")
    
    # --- Z-score standardize per feature ---
    scaler = StandardScaler()
    original_shape = X_tensor.shape
    X_flat = X_tensor.reshape(-1, n_features)
    X_flat = scaler.fit_transform(X_flat)
    X_tensor = X_flat.reshape(original_shape)
    
    # --- Only use months where we have case data (2020-2024) ---
    # The last months (2025-2026) have zero cases (not yet reported)
    time_keys = list(monthly.groupby(["year", "month"]).groups.keys())
    valid_mask = [1 if yr <= 2024 else 0 for (yr, mo) in time_keys]
    max_valid = max(i for i, v in enumerate(valid_mask) if v == 1) + 1
    
    X_tensor = X_tensor[:max_valid]
    y_tensor = y_tensor[:max_valid]
    time_periods = max_valid
    print(f"  Trimmed to {time_periods} months with case data (2020-2024)")
    
    # Normalize target
    y_mean, y_std = y_tensor.mean(), y_tensor.std()
    y_norm = (y_tensor - y_mean) / y_std
    
    # --- Create sliding windows ---
    # Each sample: input = 6 months of data, target = next month's cases
    X_windows = []
    y_windows = []
    
    for t in range(window, time_periods):
        X_windows.append(X_tensor[t - window:t])  # shape: (6, 8, 5)
        y_windows.append(y_norm[t])                 # shape: (8,)
    
    X_windows = np.array(X_windows)  # (num_samples, 6, 8, 5)
    y_windows = np.array(y_windows)  # (num_samples, 8)
    
    print(f"  Sliding windows: {X_windows.shape[0]} samples")
    print(f"  Each sample: {window} months × {n_counties} counties × {n_features} features")
    print(f"  Target: {n_counties} counties × 1 (next month cases)")
    
    return X_windows, y_windows, y_mean, y_std, scaler, feature_cols


# ============================================================
# T-GCN MODEL (Pure NumPy Implementation)
# ============================================================
# This implements the T-GCN from scratch:
#   1. GCN layer: aggregates neighbor information at each timestep
#   2. GRU cell: processes the temporal sequence (simplified LSTM)
#   3. Dense layer: maps hidden state to risk prediction

class TGCN_NumPy:
    """
    Temporal Graph Convolutional Network in pure NumPy.
    
    At each timestep t:
      1. GCN:  H_t = ReLU(A_hat @ X_t @ W_gcn)
         "Mix each county's features with its neighbors'"
         
      2. GRU:  h_t = GRU(H_t, h_{t-1})
         "Update the memory with this month's spatial info"
         
      3. Output: y = h_T @ W_out
         "Use the final memory state to predict cases"
    """
    
    def __init__(self, n_features, hidden_dim, n_counties, A_hat, lr=0.005):
        self.A_hat = A_hat          # normalized adjacency matrix
        self.hidden_dim = hidden_dim
        self.n_counties = n_counties
        self.lr = lr
        
        # --- GCN weights ---
        # Transforms input features into hidden representation
        # while incorporating neighbor information via A_hat
        scale = np.sqrt(2.0 / n_features)
        self.W_gcn = np.random.randn(n_features, hidden_dim) * scale
        self.b_gcn = np.zeros(hidden_dim)
        
        # --- GRU weights (simplified LSTM with 2 gates instead of 3) ---
        # Update gate: how much to keep old memory vs new input
        scale_h = np.sqrt(2.0 / (hidden_dim + hidden_dim))
        self.W_z = np.random.randn(hidden_dim * 2, hidden_dim) * scale_h  # update gate
        self.W_r = np.random.randn(hidden_dim * 2, hidden_dim) * scale_h  # reset gate
        self.W_h = np.random.randn(hidden_dim * 2, hidden_dim) * scale_h  # candidate
        self.b_z = np.zeros(hidden_dim)
        self.b_r = np.zeros(hidden_dim)
        self.b_h = np.zeros(hidden_dim)
        
        # --- Output layer ---
        scale_o = np.sqrt(2.0 / hidden_dim)
        self.W_out = np.random.randn(hidden_dim, 1) * scale_o
        self.b_out = np.zeros(1)
    
    def sigmoid(self, x):
        """Sigmoid activation — squashes values to (0, 1)."""
        x = np.clip(x, -15, 15)  # prevent overflow
        return 1.0 / (1.0 + np.exp(-x))
    
    def relu(self, x):
        """ReLU activation — zero out negatives."""
        return np.maximum(0, x)
    
    def tanh(self, x):
        """Tanh activation — squashes to (-1, 1)."""
        x = np.clip(x, -15, 15)
        return np.tanh(x)
    
    def forward(self, X_seq):
        """
        Forward pass through the T-GCN.
        
        X_seq shape: (window, n_counties, n_features) — e.g. (6, 8, 5)
        Returns: predictions for each county — shape (n_counties,)
        
        Step by step:
          For each month in the window:
            1. GCN: mix each county with its neighbors
            2. GRU: update the temporal memory
          After all months:
            3. Dense: predict from final memory state
        """
        window = X_seq.shape[0]
        h = np.zeros((self.n_counties, self.hidden_dim))  # initial hidden state
        
        # Store intermediates for backprop
        self.cache = {"gcn_outs": [], "h_states": [h.copy()],
                      "z_gates": [], "r_gates": [], "h_candidates": []}
        
        for t in range(window):
            X_t = X_seq[t]  # (n_counties, n_features)
            
            # --- GCN: aggregate neighbor features ---
            # A_hat @ X_t mixes each county with its neighbors
            # Then multiply by W_gcn to learn what to extract
            gcn_out = self.relu(self.A_hat @ X_t @ self.W_gcn + self.b_gcn)
            # gcn_out shape: (n_counties, hidden_dim)
            
            # --- GRU: temporal update ---
            # Concatenate spatial output with previous memory
            concat = np.concatenate([gcn_out, h], axis=1)  # (n_counties, 2*hidden)
            
            z = self.sigmoid(concat @ self.W_z + self.b_z)  # update gate
            r = self.sigmoid(concat @ self.W_r + self.b_r)  # reset gate
            
            # Candidate new memory (reset gate controls how much old memory to use)
            concat_r = np.concatenate([gcn_out, r * h], axis=1)
            h_cand = self.tanh(concat_r @ self.W_h + self.b_h)
            
            # New hidden state (update gate blends old and new)
            h = z * h + (1 - z) * h_cand
            
            # Cache for backprop
            self.cache["gcn_outs"].append(gcn_out)
            self.cache["h_states"].append(h.copy())
            self.cache["z_gates"].append(z)
            self.cache["r_gates"].append(r)
            self.cache["h_candidates"].append(h_cand)
        
        # --- Output layer ---
        y_pred = h @ self.W_out + self.b_out  # (n_counties, 1)
        return y_pred.flatten()  # (n_counties,)
    
    def compute_loss(self, y_pred, y_true):
        """Mean Squared Error loss."""
        return np.mean((y_pred - y_true) ** 2)
    
    def train_step(self, X_seq, y_true):
        """
        One training step: forward pass + numerical gradient update.
        
        We use numerical gradients (finite differences) instead of
        full backpropagation. It's slower but much simpler to implement
        and debug — perfect for a hackathon.
        
        For the PyTorch version (bottom of file), autograd handles
        this automatically and much faster.
        """
        # Forward pass
        y_pred = self.forward(X_seq)
        loss = self.compute_loss(y_pred, y_true)
        
        # --- Gradient via finite differences ---
        # Compute gradient for output layer analytically (this one's easy)
        h_final = self.cache["h_states"][-1]  # (n_counties, hidden)
        error = 2 * (y_pred - y_true) / len(y_true)  # dL/dy, shape (n_counties,)
        
        # Gradient for W_out: h_final^T @ error
        dW_out = h_final.T @ error.reshape(-1, 1)  # (hidden, 1)
        db_out = error.sum()
        
        # Update output layer
        self.W_out -= self.lr * np.clip(dW_out, -1, 1)
        self.b_out -= self.lr * np.clip(db_out, -1, 1)
        
        # For GCN and GRU weights: use finite differences
        # (This is the hacky-but-works approach for the hackathon)
        eps = 1e-4
        for param_name in ["W_gcn", "b_gcn", "W_z", "W_r", "W_h"]:
            param = getattr(self, param_name)
            grad = np.zeros_like(param)
            
            # Only update a random subset of weights each step (stochastic)
            # This makes training 50x faster while still converging
            n_update = min(20, param.size)
            indices = np.random.choice(param.size, n_update, replace=False)
            
            for idx in indices:
                flat = param.flat
                old_val = flat[idx]
                
                flat[idx] = old_val + eps
                loss_plus = self.compute_loss(self.forward(X_seq), y_true)
                
                flat[idx] = old_val - eps
                loss_minus = self.compute_loss(self.forward(X_seq), y_true)
                
                flat[idx] = old_val
                grad.flat[idx] = (loss_plus - loss_minus) / (2 * eps)
            
            # Update with gradient clipping
            setattr(self, param_name, param - self.lr * np.clip(grad, -1, 1))
        
        return loss


# ============================================================
# TRAINING LOOP
# ============================================================

def train_tgcn(X_windows, y_windows, A_hat, epochs=60, hidden_dim=16):
    """
    Train the T-GCN with train/test split.
    
    Split: first 80% of time periods for training, last 20% for testing.
    This is a temporal split (not random) because we're predicting the future.
    """
    print("\n" + "=" * 60)
    print("TRAINING: T-GCN (Temporal Graph Convolutional Network)")
    print("=" * 60)
    
    n_samples = len(X_windows)
    n_features = X_windows.shape[3]
    n_counties = X_windows.shape[2]
    
    # Temporal train/test split (80/20)
    split = int(n_samples * 0.8)
    X_train, X_test = X_windows[:split], X_windows[split:]
    y_train, y_test = y_windows[:split], y_windows[split:]
    
    print(f"\n  Architecture: GCN({n_features}→{hidden_dim}) → GRU({hidden_dim}) → Dense({hidden_dim}→1)")
    print(f"  Graph: {n_counties} county nodes, {len(EDGES)} edges")
    print(f"  Window: {X_windows.shape[1]} months lookback")
    print(f"  Train: {len(X_train)} samples | Test: {len(X_test)} samples")
    print(f"  Training for {epochs} epochs...")
    print()
    
    # Initialize model
    model = TGCN_NumPy(
        n_features=n_features,
        hidden_dim=hidden_dim,
        n_counties=n_counties,
        A_hat=A_hat,
        lr=0.005
    )
    
    # Training loop
    best_test_loss = float("inf")
    train_losses = []
    test_losses = []
    
    for epoch in range(epochs):
        # --- Train ---
        epoch_loss = 0
        for i in range(len(X_train)):
            loss = model.train_step(X_train[i], y_train[i])
            epoch_loss += loss
        avg_train = epoch_loss / len(X_train)
        train_losses.append(avg_train)
        
        # --- Test ---
        test_loss = 0
        test_preds = []
        for i in range(len(X_test)):
            pred = model.forward(X_test[i])
            test_preds.append(pred)
            test_loss += model.compute_loss(pred, y_test[i])
        avg_test = test_loss / len(X_test)
        test_losses.append(avg_test)
        
        if avg_test < best_test_loss:
            best_test_loss = avg_test
        
        # Print progress every 10 epochs
        if (epoch + 1) % 10 == 0 or epoch == 0:
            print(f"  Epoch {epoch+1:3d}/{epochs}  |  Train Loss: {avg_train:.4f}  |  Test Loss: {avg_test:.4f}")
    
    # --- Final evaluation ---
    all_preds = []
    all_true = []
    for i in range(len(X_test)):
        pred = model.forward(X_test[i])
        all_preds.append(pred)
        all_true.append(y_test[i])
    
    all_preds = np.array(all_preds)  # (test_samples, 8)
    all_true = np.array(all_true)
    
    return model, all_preds, all_true, train_losses, test_losses, split


# ============================================================
# EVALUATION AND COMPARISON
# ============================================================

def evaluate_and_save(all_preds, all_true, y_mean, y_std, split,
                      csv_path="sporerisk_master_corrected.csv"):
    """
    Denormalize predictions, compute metrics, save results.
    """
    print("\n" + "=" * 60)
    print("EVALUATION")
    print("=" * 60)
    
    # Denormalize
    preds_real = all_preds * y_std + y_mean
    true_real = all_true * y_std + y_mean
    
    # Overall metrics
    rmse = np.sqrt(mean_squared_error(true_real.flatten(), preds_real.flatten()))
    mae = mean_absolute_error(true_real.flatten(), preds_real.flatten())
    r2 = r2_score(true_real.flatten(), preds_real.flatten())
    
    print(f"\n  T-GCN Test Results (temporal split):")
    print(f"    RMSE:  {rmse:.2f} cases/month")
    print(f"    MAE:   {mae:.2f} cases/month")
    print(f"    R²:    {r2:.4f}")
    
    # Per-county metrics
    print(f"\n  PER-COUNTY TEST PERFORMANCE:")
    print("  " + "-" * 55)
    print(f"  {'County':15s} {'Avg Actual':>12s} {'Avg Predicted':>14s} {'MAE':>8s}")
    print("  " + "-" * 55)
    
    for ci, county in enumerate(COUNTIES):
        county_true = true_real[:, ci]
        county_pred = preds_real[:, ci]
        c_mae = mean_absolute_error(county_true, county_pred)
        print(f"  {county:15s} {county_true.mean():12.1f} {county_pred.mean():14.1f} {c_mae:8.1f}")
    
    # ── Convert predicted cases → Sporisk-equivalent risk tier ──────────────
    # The T-GCN predicts case counts, not a Gpot×Erisk score. To make its
    # output comparable to the Sporisk index we use county-relative historical
    # percentiles: if this month's predicted cases are in the top 25% for that
    # county, that's "Very High" — matching the biological severity scale.
    # We also compute a normalized 0-100 pseudo-score so the frontend can
    # display T-GCN predictions on the same axis as baseline_predictions.csv.
    #
    # NOTE: This is a case-count → severity mapping, NOT a Gpot×Erisk
    # computation. The T-GCN learns the full weather→cases relationship
    # end-to-end so Gpot/Erisk components are implicit, not explicit.

    # Build per-county case history for percentile thresholds
    # (use all true_real values as the reference distribution)
    county_case_history = {}
    for ci, county in enumerate(COUNTIES):
        county_case_history[county] = true_real[:, ci]

    def cases_to_sporisk_tier(predicted, county):
        """
        Map predicted case count to risk tier using county percentiles,
        then return a pseudo-score scaled to 0-100.

        Percentile thresholds:
          < p25  → Low        → pseudo-score: predicted/p25 * 3        (0–3)
          < p50  → Moderate   → pseudo-score: 3 + (pred-p25)/(p50-p25)*5   (3–8)
          < p75  → High       → pseudo-score: 8 + (pred-p50)/(p75-p50)*7   (8–15)
          ≥ p75  → Very High  → pseudo-score: 15 + min((pred-p75)/p75*10,10)(15–25)

        These bands match the Sporisk fixed thresholds (<3/3-8/8-15/≥15)
        so tiers are directly comparable between models.
        """
        hist = county_case_history[county]
        p25, p50, p75 = np.percentile(hist, 25), np.percentile(hist, 50), np.percentile(hist, 75)

        if predicted < p25:
            tier = "Low"
            score = (predicted / max(p25, 0.1)) * 3
        elif predicted < p50:
            tier = "Moderate"
            score = 3 + ((predicted - p25) / max(p50 - p25, 0.1)) * 5
        elif predicted < p75:
            tier = "High"
            score = 8 + ((predicted - p50) / max(p75 - p50, 0.1)) * 7
        else:
            tier = "Very High"
            score = 15 + min(((predicted - p75) / max(p75, 0.1)) * 10, 10)

        return tier, round(max(0.0, score), 2)

    # Save predictions with tier and pseudo-score
    rows = []
    for t in range(len(all_preds)):
        for ci, county in enumerate(COUNTIES):
            pred = preds_real[t, ci]
            tier, pseudo_score = cases_to_sporisk_tier(pred, county)
            rows.append({
                "county":           county,
                "test_sample":      t,
                "actual_cases":     true_real[t, ci],
                "predicted_cases":  pred,
                "residual":         true_real[t, ci] - pred,
                # Sporisk-equivalent fields so API/frontend can treat both
                # models consistently. Label clearly as case-derived.
                "risk_score":       pseudo_score,   # 0–100, case-count derived
                "predicted_risk":   tier,           # Low/Moderate/High/Very High
                "score_method":     "case_percentile",  # NOT Gpot×Erisk
            })

    results = pd.DataFrame(rows)
    _out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tgcn_predictions.csv")
    results.to_csv(_out, index=False)
    print(f"\n  Saved → {_out}")
    print(f"\n  Saved → tgcn_predictions.csv")
    print(f"  Columns: {list(results.columns)}")
    print(f"\n  T-GCN Risk Tier Distribution (case-percentile method):")
    for tier in ["Low", "Moderate", "High", "Very High"]:
        n = (results["predicted_risk"] == tier).sum()
        pct = n / len(results) * 100
        print(f"    {tier:12s}: {n:>4} rows ({pct:.1f}%)")
    print(f"\n  NOTE: risk_score here is case-count → percentile derived,")
    print(f"  NOT Gpot×Erisk. score_method='case_percentile' marks this.")

    return rmse, mae, r2


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  SPORERISK - T-GCN (LSTM + GNN)")
    print("  Spatio-Temporal Valley Fever Prediction")
    print("=" * 60)
    
    # Build adjacency graph
    print("\nBuilding county adjacency graph...")
    A_hat = build_adjacency_matrix()
    
    # Prepare sequences
    X, y, y_mean, y_std, scaler, features = prepare_sequences(
        csv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "sporerisk_master_corrected.csv"),
        window=6  # 6-month lookback
    )
    
    # Train T-GCN
    model, preds, true, train_loss, test_loss, split = train_tgcn(
        X, y, A_hat,
        epochs=60,
        hidden_dim=16
    )
    
    # Evaluate
    rmse, mae, r2 = evaluate_and_save(preds, true, y_mean, y_std, split)
    
    print("\n" + "=" * 60)
    print("  DONE!")
    print("  " + "-" * 40)
    print("  Your team now has two models:")
    print("  1. Random Forest baseline (model_baseline.py)")
    print("  2. T-GCN deep learning   (model_tgcn.py)")
    print("  ")
    print("  For your pitch, show both and compare!")
    print("=" * 60)


# ============================================================
# PYTORCH VERSION (for your team's machines)
# ============================================================
# Uncomment this and run locally where PyTorch is installed.
# It's faster and supports proper backpropagation.

"""
import torch
import torch.nn as nn

class TGCN_PyTorch(nn.Module):
    def __init__(self, n_features, hidden_dim, n_counties, A_hat):
        super().__init__()
        self.A_hat = torch.FloatTensor(A_hat)
        self.hidden_dim = hidden_dim
        self.n_counties = n_counties
        
        # GCN layer
        self.W_gcn = nn.Linear(n_features, hidden_dim)
        
        # GRU cell (built-in PyTorch — handles gates automatically)
        self.gru = nn.GRUCell(hidden_dim, hidden_dim)
        
        # Output layer
        self.fc_out = nn.Linear(hidden_dim, 1)
    
    def forward(self, X_seq):
        # X_seq: (batch, window, n_counties, n_features)
        batch_size, window, N, F = X_seq.shape
        h = torch.zeros(batch_size * N, self.hidden_dim)
        
        for t in range(window):
            X_t = X_seq[:, t]  # (batch, N, F)
            
            # GCN: aggregate neighbors
            # A_hat @ X_t mixes each county with neighbors
            X_graph = torch.matmul(self.A_hat, X_t)  # (batch, N, F)
            gcn_out = torch.relu(self.W_gcn(X_graph))  # (batch, N, hidden)
            
            # Reshape for GRU: (batch*N, hidden)
            gcn_flat = gcn_out.reshape(batch_size * N, -1)
            h = self.gru(gcn_flat, h)
        
        # Output: (batch*N, hidden) → (batch*N, 1) → (batch, N)
        out = self.fc_out(h).reshape(batch_size, N)
        return out


# Training loop for PyTorch version:
#
# model = TGCN_PyTorch(n_features=5, hidden_dim=32, n_counties=8, A_hat=A_hat)
# optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
# criterion = nn.MSELoss()
#
# for epoch in range(100):
#     optimizer.zero_grad()
#     X_batch = torch.FloatTensor(X_train)  # (batch, 6, 8, 5)
#     y_batch = torch.FloatTensor(y_train)  # (batch, 8)
#     y_pred = model(X_batch)
#     loss = criterion(y_pred, y_batch)
#     loss.backward()   # autograd computes ALL gradients automatically
#     optimizer.step()
#     print(f"Epoch {epoch}: Loss = {loss.item():.4f}")
"""
