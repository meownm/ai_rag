import { Card } from '@/components/ui/Card';

export function AnswerPanel({ answer, refusal }: { answer?: string; refusal?: string }) {
  return (
    <Card>
      <h2 className="mb-2 text-lg font-semibold">Answer</h2>
      {refusal ? <p className="text-red-700">Refusal: {refusal}</p> : <p className="whitespace-pre-wrap">{answer ?? 'No answer yet.'}</p>}
    </Card>
  );
}
