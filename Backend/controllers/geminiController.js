import { GoogleGenerativeAI } from "@google/generative-ai";

const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);
const model = genAI.getGenerativeModel({ model: "gemini-1.5-flash" });

export const generateRiskSummary = async (req, res) => {
    const { riskData, environmentalData } = req.body;

    // The prompt that powers the "AI Risk Summary" look
    const prompt = `
    Based on this Valley Fever data, write a concise AI Risk Summary:
    - Risk Index: ${riskData.index}
    - Wind: ${environmentalData.windSpeed} km/h
    - Dust (PM10): ${environmentalData.dustLevel} µg/m³
    - Precipitation: ${environmentalData.precip} mm
    
    Format the output as a few bullet points focusing on airborne exposure risks.
  `;

    try {
        const result = await model.generateContent(prompt);
        res.json({ summary: result.response.text() });
    } catch (error) {
        res.status(500).json({ error: "Gemini integration failed" });
    }
};