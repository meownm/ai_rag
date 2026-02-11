import { FormEvent, useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';

export function QueryInputCard({ onSubmit, loading }: { onSubmit: (query: string) => void; loading: boolean }) {
  const [query, setQuery] = useState('');

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (query.trim().length > 0) {
      onSubmit(query.trim());
    }
  };

  return (
    <Card>
      <form className="flex gap-2" onSubmit={submit}>
        <Input placeholder="Ask a question..." value={query} onChange={(event) => setQuery(event.target.value)} />
        <Button type="submit" disabled={loading}>
          {loading ? 'Searching...' : 'Search'}
        </Button>
      </form>
    </Card>
  );
}
