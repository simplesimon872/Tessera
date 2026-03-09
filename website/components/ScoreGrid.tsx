'use client'

import { useEffect, useState } from 'react'

interface ScoreRowProps {
  label: string
  value: number | null | undefined
  delay?: number
  accent?: boolean
}

export function ScoreRow({ label, value, delay = 0, accent = false }: ScoreRowProps) {
  const [animated, setAnimated] = useState(false)
  const displayValue = value ?? 0
  const formatted = value !== null && value !== undefined ? value.toFixed(1) : '—'

  useEffect(() => {
    const t = setTimeout(() => setAnimated(true), delay)
    return () => clearTimeout(t)
  }, [delay])

  return (
    <div>
      <div className="flex justify-between items-baseline mb-1.5">
        <span className={`font-sans text-sm ${accent ? 'font-bold text-primary' : 'font-medium text-primary'}`}>
          {label}
        </span>
        <span className={`font-mono text-sm ${accent ? 'text-accent font-medium' : 'text-accent'}`}>
          {formatted}
        </span>
      </div>
      <div className="h-px bg-border w-full relative overflow-hidden">
        <div
          className="h-px absolute left-0 top-0 transition-all duration-700 ease-out"
          style={{
            width: animated ? `${Math.min(displayValue, 100)}%` : '0%',
            background: accent ? '#E8FF47' : '#E8FF4799',
          }}
        />
      </div>
    </div>
  )
}

interface ScoreGridProps {
  scores: {
    composite?: number | null
    originality?: number | null
    focus?: number | null
    consistency?: number | null
    depth?: number | null
  }
}

export function ScoreGrid({ scores }: ScoreGridProps) {
  return (
    <div className="space-y-4">
      <ScoreRow label="Composite"   value={scores.composite}   delay={0}   accent />
      <div className="h-px bg-border my-2" />
      <ScoreRow label="Originality" value={scores.originality} delay={100} />
      <ScoreRow label="Focus"       value={scores.focus}       delay={180} />
      <ScoreRow label="Consistency" value={scores.consistency} delay={260} />
      <ScoreRow label="Depth"       value={scores.depth}       delay={340} />
    </div>
  )
}
