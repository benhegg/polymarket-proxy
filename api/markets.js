export default async function handler(req, res) {
  // Enable CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  
  // Handle preflight
  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  try {
    // Fetch from Polymarket
    const response = await fetch(
      'https://gamma-api.polymarket.com/markets?active=true&closed=false&limit=50'
    );
    
    if (!response.ok) {
      throw new Error(`Polymarket API returned ${response.status}`);
    }
    
    const data = await response.json();
    
    // Return the data
    return res.status(200).json(data);
    
  } catch (error) {
    console.error('API Error:', error);
    return res.status(500).json({ 
      error: error.message,
      timestamp: new Date().toISOString()
    });
  }
}
