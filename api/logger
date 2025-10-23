import { kv } from '@vercel/kv';

export default async function handler(req, res) {
  // CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  
  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  try {
    console.log('[Logger] Starting snapshot...');
    
    // Fetch current market data
    const response = await fetch(
      'https://gamma-api.polymarket.com/markets?active=true&closed=false&limit=50'
    );
    
    if (!response.ok) {
      throw new Error(`Polymarket API error: ${response.status}`);
    }
    
    const markets = await response.json();
    const timestamp = Date.now();
    
    // Save snapshot
    const snapshot = {
      timestamp,
      datetime: new Date().toISOString(),
      markets: markets.map(m => ({
        id: m.id,
        question: m.question,
        category: m.category,
        volume: parseFloat(m.volume || 0),
        liquidity: parseFloat(m.liquidity || 0),
        price: JSON.parse(m.outcomePrices || '["0.5"]')[0]
      }))
    };
    
    // Store snapshot with timestamp as key
    await kv.set(`snapshot:${timestamp}`, snapshot);
    
    // Keep a list of snapshot timestamps for easy retrieval
    const snapshotList = await kv.get('snapshot-list') || [];
    snapshotList.push(timestamp);
    
    // Keep only last 1000 snapshots (about 3 days at 5min intervals)
    if (snapshotList.length > 1000) {
      const oldTimestamp = snapshotList.shift();
      await kv.del(`snapshot:${oldTimestamp}`);
    }
    
    await kv.set('snapshot-list', snapshotList);
    
    console.log(`[Logger] ✅ Saved snapshot with ${markets.length} markets`);
    
    return res.status(200).json({
      success: true,
      timestamp,
      marketCount: markets.length,
      totalSnapshots: snapshotList.length
    });
    
  } catch (error) {
    console.error('[Logger] Error:', error);
    return res.status(500).json({ 
      error: error.message 
    });
  }
}
