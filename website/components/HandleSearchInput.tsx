'use client'

import { useState } from 'react'

export default function HandleSearchInput() {
  const [handle, setHandle] = useState('')

  const navigate = () => {
    const clean = handle.replace('@', '').trim().toLowerCase()
    if (clean) window.location.href = `/${clean}`
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') navigate()
  }

  return (
    <div className="flex flex-col sm:flex-row gap-0 max-w-sm mx-auto w-full">
      <div className="flex-1 flex items-center border border-border bg-surface px-4">
        <span className="font-mono text-muted text-sm mr-1">@</span>
        <input
          type="text"
          placeholder="handle"
          value={handle}
          onChange={e => setHandle(e.target.value)}
          onKeyDown={handleKeyDown}
          className="flex-1 bg-transparent font-mono text-sm text-primary placeholder-muted outline-none py-3"
          autoComplete="off"
          spellCheck={false}
        />
      </div>
      <button
        type="button"
        onClick={navigate}
        className="bg-accent text-bg font-mono text-sm font-medium px-6 py-3 hover:bg-primary transition-colors whitespace-nowrap tracking-wide"
      >
        View record →
      </button>
    </div>
  )
}
