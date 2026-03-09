'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

export default function HandleSearchInput() {
  const [handle, setHandle] = useState('')
  const router = useRouter()

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const clean = handle.replace('@', '').trim().toLowerCase()
    if (clean) router.push(`/${clean}`)
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-0 max-w-sm mx-auto w-full">
      <div className="flex-1 flex items-center border border-border bg-surface px-4">
        <span className="font-mono text-muted text-sm mr-1">@</span>
        <input
          type="text"
          placeholder="handle"
          value={handle}
          onChange={e => setHandle(e.target.value)}
          className="flex-1 bg-transparent font-mono text-sm text-primary placeholder-muted outline-none py-3"
          autoComplete="off"
          spellCheck={false}
        />
      </div>
      <button
        type="submit"
        className="bg-accent text-bg font-mono text-sm font-medium px-6 py-3 hover:bg-primary transition-colors whitespace-nowrap tracking-wide"
      >
        View record →
      </button>
    </form>
  )
}
