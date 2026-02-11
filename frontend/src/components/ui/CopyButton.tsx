import { useState } from 'react';
import { Button } from './Button';

export function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <Button
      type="button"
      className="bg-slate-700 hover:bg-slate-800"
      onClick={async () => {
        await navigator.clipboard.writeText(text);
        setCopied(true);
      }}
    >
      {copied ? 'Copied' : 'Copy'}
    </Button>
  );
}
