# 🚀 Quick Start: Build Video Chain Finder V2

**Goal**: Create a modern Next.js prototype with AI features in 1 week

---

## Day 1: Setup (2 hours)

### 1. Create Next.js Project

```bash
cd /Users/alialqattan/Downloads/8xSovia/

# Create new Next.js app
npx create-next-app@latest video-chains-v2 \
  --typescript \
  --tailwind \
  --app \
  --src-dir \
  --import-alias "@/*"

cd video-chains-v2
```

### 2. Install Dependencies

```bash
# UI Components
npm install @radix-ui/react-dialog \
            @radix-ui/react-dropdown-menu \
            @radix-ui/react-slider \
            @radix-ui/react-select \
            lucide-react \
            class-variance-authority \
            clsx \
            tailwind-merge

# Video & Visualization
npm install video.js \
            @types/video.js \
            reactflow \
            @dnd-kit/core \
            @dnd-kit/sortable

# State & API
npm install zustand \
            @tanstack/react-query \
            axios

# Development
npm install -D @types/node \
               @types/react \
               @types/react-dom
```

### 3. Set Up shadcn/ui

```bash
npx shadcn-ui@latest init

# Add components
npx shadcn-ui@latest add button
npx shadcn-ui@latest add card
npx shadcn-ui@latest add dialog
npx shadcn-ui@latest add input
npx shadcn-ui@latest add slider
npx shadcn-ui@latest add tabs
```

---

## Day 2: Core Components (4 hours)

### 1. Create API Client

```typescript
// src/lib/api.ts
import axios from 'axios';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

export const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json'
  }
});

export async function getChains(params: {
  minScore?: number;
  minLength?: number;
}) {
  const { data } = await api.get('/api/chains/smart', { params });
  return data;
}

export async function getApiInfo() {
  const { data } = await api.get('/api/info');
  return data;
}
```

### 2. Create Video Player Component

```typescript
// src/components/video-player.tsx
'use client';

import { useEffect, useRef } from 'react';
import videojs from 'video.js';
import 'video.js/dist/video-js.css';

interface VideoPlayerProps {
  src: string;
  onEnded?: () => void;
}

export function VideoPlayer({ src, onEnded }: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const playerRef = useRef<any>(null);

  useEffect(() => {
    if (!videoRef.current) return;

    const player = videojs(videoRef.current, {
      controls: true,
      fluid: true,
      sources: [{ src, type: 'video/mp4' }]
    });

    if (onEnded) {
      player.on('ended', onEnded);
    }

    playerRef.current = player;

    return () => {
      if (playerRef.current) {
        playerRef.current.dispose();
      }
    };
  }, [src, onEnded]);

  return (
    <div data-vjs-player>
      <video
        ref={videoRef}
        className="video-js vjs-big-play-centered"
      />
    </div>
  );
}
```

### 3. Create Chain Card Component

```typescript
// src/components/chain-card.tsx
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface ChainCardProps {
  chain: {
    length: number;
    avg_quality: number;
    total_duration: number;
    videos: any[];
  };
  onClick?: () => void;
}

export function ChainCard({ chain, onClick }: ChainCardProps) {
  const qualityColor = chain.avg_quality > 0.8 ? 'green'
                     : chain.avg_quality > 0.6 ? 'yellow'
                     : 'red';

  return (
    <Card
      className="cursor-pointer hover:shadow-lg transition-shadow"
      onClick={onClick}
    >
      <CardHeader>
        <CardTitle className="flex justify-between items-center">
          <span>{chain.length} Videos</span>
          <Badge variant={qualityColor}>
            {(chain.avg_quality * 100).toFixed(0)}%
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2 text-sm text-muted-foreground">
          <div>Duration: {chain.total_duration.toFixed(1)}s</div>
          <div>Quality: {chain.avg_quality.toFixed(3)}</div>
        </div>
      </CardContent>
    </Card>
  );
}
```

---

## Day 3: Main Pages (4 hours)

### 1. Dashboard Page

```typescript
// src/app/page.tsx
'use client';

import { useQuery } from '@tanstack/react-query';
import { getApiInfo, getChains } from '@/lib/api';
import { ChainCard } from '@/components/chain-card';
import { Button } from '@/components/ui/button';

export default function Dashboard() {
  const { data: info } = useQuery({
    queryKey: ['api-info'],
    queryFn: getApiInfo
  });

  const { data: chains } = useQuery({
    queryKey: ['chains', 0.6, 2],
    queryFn: () => getChains({ minScore: 0.6, minLength: 2 })
  });

  return (
    <div className="container mx-auto p-8">
      <header className="mb-8">
        <h1 className="text-4xl font-bold mb-2">
          🧠 Smart Video Chain Finder
        </h1>
        <p className="text-muted-foreground">
          {info?.message} • {info?.version}
        </p>
      </header>

      <div className="grid gap-6 md:grid-cols-3 mb-8">
        <StatCard
          title="Videos"
          value={info?.videos || 0}
          icon="🎬"
        />
        <StatCard
          title="Chains Found"
          value={chains?.total_chains || 0}
          icon="🔗"
        />
        <StatCard
          title="Smart Mode"
          value={info?.smart_mode ? "Active" : "Inactive"}
          icon="🧠"
        />
      </div>

      <section>
        <h2 className="text-2xl font-bold mb-4">Top Quality Chains</h2>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {chains?.chains?.slice(0, 6).map((chain, i) => (
            <ChainCard key={i} chain={chain} />
          ))}
        </div>
      </section>
    </div>
  );
}
```

### 2. Discover Page

```typescript
// src/app/discover/page.tsx
'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getChains } from '@/lib/api';
import { ChainCard } from '@/components/chain-card';
import { Slider } from '@/components/ui/slider';
import { Input } from '@/components/ui/input';

export default function DiscoverPage() {
  const [minScore, setMinScore] = useState(0.6);
  const [minLength, setMinLength] = useState(2);

  const { data: chains, isLoading } = useQuery({
    queryKey: ['chains', minScore, minLength],
    queryFn: () => getChains({ minScore, minLength })
  });

  return (
    <div className="container mx-auto p-8">
      <h1 className="text-4xl font-bold mb-8">Discover Chains</h1>

      <div className="bg-card p-6 rounded-lg mb-8">
        <h2 className="font-semibold mb-4">Filters</h2>

        <div className="space-y-4">
          <div>
            <label className="text-sm text-muted-foreground">
              Min Quality: {minScore.toFixed(2)}
            </label>
            <Slider
              value={[minScore]}
              onValueChange={([v]) => setMinScore(v)}
              min={0}
              max={1}
              step={0.05}
              className="mt-2"
            />
          </div>

          <div>
            <label className="text-sm text-muted-foreground">
              Min Length
            </label>
            <Input
              type="number"
              value={minLength}
              onChange={(e) => setMinLength(Number(e.target.value))}
              min={2}
              max={10}
              className="mt-2"
            />
          </div>
        </div>
      </div>

      {isLoading ? (
        <div>Loading chains...</div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {chains?.chains?.map((chain, i) => (
            <ChainCard key={i} chain={chain} />
          ))}
        </div>
      )}
    </div>
  );
}
```

---

## Day 4: AI Integration (4 hours)

### 1. Set Up Environment Variables

```bash
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:8001
GEMINI_API_KEY=AIzaSyAObfIFoHQDBhnzlhrA-SkfCBQTh7TkpNE
ELEVENLABS_API_KEY=sk_d2e36b7f05adf5c54215014a737953e096e5bd42ac64bc35
```

### 2. Create AI Route Handler

```typescript
// src/app/api/narration/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { GoogleGenerativeAI } from '@google/generative-ai';

const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY!);

export async function POST(request: NextRequest) {
  const { chain } = await request.json();

  try {
    const model = genAI.getGenerativeModel({ model: 'gemini-pro' });

    const prompt = `
    Create a compelling narrative for this video chain:

    ${chain.videos.map((v, i) => `${i + 1}. ${v.filename} (${v.duration}s)`).join('\n')}

    Style: Documentary
    Length: ~50 words
    Tone: Engaging and natural
    `;

    const result = await model.generateContent(prompt);
    const narrative = result.response.text();

    return NextResponse.json({ narrative });
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to generate narrative' },
      { status: 500 }
    );
  }
}
```

### 3. Add Narration Button to Chain Card

```typescript
// src/components/chain-card.tsx (updated)
'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';

export function ChainCard({ chain }: ChainCardProps) {
  const [narrative, setNarrative] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function generateNarrative() {
    setLoading(true);
    try {
      const res = await fetch('/api/narration', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chain })
      });
      const data = await res.json();
      setNarrative(data.narrative);
    } catch (error) {
      console.error('Failed to generate narrative:', error);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      {/* ... existing code ... */}

      <CardContent>
        <Button
          onClick={generateNarrative}
          disabled={loading}
          className="w-full mt-4"
        >
          {loading ? 'Generating...' : '🎭 Generate Narration'}
        </Button>

        {narrative && (
          <div className="mt-4 p-3 bg-muted rounded text-sm">
            {narrative}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
```

---

## Day 5: Polish & Deploy (3 hours)

### 1. Add Loading States

```typescript
// src/components/loading-skeleton.tsx
export function ChainCardSkeleton() {
  return (
    <Card>
      <CardHeader>
        <div className="h-6 bg-muted animate-pulse rounded" />
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          <div className="h-4 bg-muted animate-pulse rounded" />
          <div className="h-4 bg-muted animate-pulse rounded w-3/4" />
        </div>
      </CardContent>
    </Card>
  );
}
```

### 2. Add Error Handling

```typescript
// src/components/error-boundary.tsx
'use client';

import { useEffect } from 'react';

export function ErrorBoundary({
  error,
  reset
}: {
  error: Error;
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex flex-col items-center justify-center p-8">
      <h2 className="text-2xl font-bold mb-4">Something went wrong!</h2>
      <Button onClick={reset}>Try again</Button>
    </div>
  );
}
```

### 3. Deploy to Vercel

```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
vercel

# Follow prompts:
# - Link to existing project or create new
# - Configure environment variables
# - Deploy!
```

---

## Testing the Prototype

### 1. Start Development Server

```bash
npm run dev
```

Visit: `http://localhost:3000`

### 2. Test Checklist

- [ ] Dashboard loads with stats
- [ ] Chains display correctly
- [ ] Filters work (quality, length)
- [ ] AI narration generates
- [ ] Video player works
- [ ] Mobile responsive
- [ ] Dark mode works

### 3. User Test Script

Ask 3-5 people to:

1. "Find a high-quality chain"
2. "Generate a narration for it"
3. "What would make this better?"

---

## Next Steps After Prototype

### Week 2: Enhanced Features
- Timeline editor with drag-drop
- Video preview in modal
- Export to MP4 functionality

### Week 3: Mobile UI
- Touch gestures
- Swipeable cards
- Mobile video player

### Week 4: Launch
- Performance optimization
- SEO & metadata
- Product Hunt launch
- Get first 100 users

---

## Quick Commands Reference

```bash
# Development
npm run dev

# Build for production
npm run build

# Start production server
npm start

# Type checking
npm run type-check

# Linting
npm run lint

# Deploy to Vercel
vercel --prod
```

---

## Resources

- **Next.js Docs**: https://nextjs.org/docs
- **shadcn/ui**: https://ui.shadcn.com
- **Tailwind CSS**: https://tailwindcss.com/docs
- **Video.js**: https://videojs.com/guides
- **Gemini AI**: https://ai.google.dev/docs
- **React Query**: https://tanstack.com/query/latest

---

**Goal**: Ship a working prototype by end of Week 1, get user feedback, iterate!

🚀 Let's transform this into something amazing!
