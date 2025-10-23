import { kv } from '@vercel/kv';

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  
  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  try {
    const snapshotList = await kv.get('snapshot-list') || [];
    
    if (snapshotList.length < 2) {
      return res.status(200).json({
        message: 'Not enough data yet. Need at least 2 snapshots.',
        snapshotCount: snapshotList.length
      });
    }
    
    // Get current and 1 hour ago snapshots
    const currentTimestamp = snapshotList[snapshotList.length - 1];
    const current = await kv.get(`snapshot:${currentTimestamp}`);
    
    // Find snapshot from ~1 hour ago (12 snapshots at 5min intervals)
    const hourAgoIndex = Math.max(0, snapshotList.length - 13);
    const hourAgoTimestamp = snapshotList[hourAgoIndex];
    const hourAgo = await kv.get(`snapshot:${hourAgoTimestamp}`);
    
    if (!current || !hourAgo) {
      return res.status(500).json({ error: 'Missing snapshot data' });
    }
    
    // Calculate velocity for each market
    const analytics = current.markets.map(currentMarket => {
      const oldMarket = hourAgo.markets.find(m => m.id === currentMarket.id);
      
      if (!oldMarket) {
        return {
          ...currentMarket,
          volumeChange: 0,
          priceChange: 0,
          velocity: 0
        };
      }
      
      const volumeChange = currentMarket.volume - oldMarket.volume;
      const volumeChangePercent = oldMarket.volume > 0 
        ? (volumeChange / oldMarket.volume) * 100 
        : 0;
      
      const priceChange = currentMarket.price - oldMarket.price;
      const priceChangePercent = oldMarket.price > 0
        ? (priceChange / oldMarket.price) * 100
        : 0;
      
      // Calculate velocity score (0-100)
      let velocity = 0;
      
      // Volume velocity (0-40 points)
      if (volumeChangePercent > 50) velocity += 40;
      else if (volumeChangePercent > 20) velocity += 30;
      else if (volumeChangePercent > 10) velocity += 20;
      else if (volumeChangePercent > 5) velocity += 10;
      
      // Price momentum (0-30 points)
      const absPriceChange = Math.abs(priceChangePercent);
      if (absPriceChange > 10) velocity += 30;
      else if (absPriceChange > 5) velocity += 20;
      else if (absPriceChange > 2) velocity += 10;
      
      // Liquidity ratio (0-20 points)
      const liqRatio = currentMarket.liquidity / currentMarket.volume;
      if (liqRatio > 0.15) velocity += 20;
      else if (liqRatio > 0.10) velocity += 15;
      else if (liqRatio > 0.05) velocity += 10;
      
      // Absolute volume (0-10 points)
      if (currentMarket.volume > 20000000) velocity += 10;
      else if (currentMarket.volume > 10000000) velocity += 5;
      
      return {
        ...currentMarket,
        volumeChange,
        volumeChangePercent: volumeChangePercent.toFixed(2),
        priceChange: priceChange.toFixed(4),
        priceChangePercent: priceChangePercent.toFixed(2),
        velocity: Math.round(velocity),
        hoursTracked: ((currentTimestamp - hourAgoTimestamp) / (1000 * 60 * 60)).toFixed(1)
      };
    });
    
    // Sort by velocity score
    analytics.sort((a, b) => b.velocity - a.velocity);
    
    return res.status(200).json({
      timestamp: current.datetime,
      compareTimestamp: hourAgo.datetime,
      markets: analytics,
      snapshotCount: snapshotList.length
    });
    
  } catch (error) {
    console.error('[Analytics] Error:', error);
    return res.status(500).json({ error: error.message });
  }
}
