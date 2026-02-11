import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ScoringTraceDrawer } from '@/components/query/ScoringTraceDrawer';

describe('ScoringTraceDrawer', () => {
  it('shows all scoring fields', () => {
    render(
      <ScoringTraceDrawer
        citations={[
          {
            chunk_id: 'c1',
            document_id: 'd1',
            title: 'Doc',
            url: 'http://x',
            snippet: 'snippet',
            score_breakdown: { lex_score: 0.1, vec_score: 0.2, rerank_score: 0.3, boosts: { recency: 1 }, final_score: 1.6 },
          },
        ]}
      />,
    );

    expect(screen.getByText(/lex_score/)).toBeInTheDocument();
    expect(screen.getByText(/vec_score/)).toBeInTheDocument();
    expect(screen.getByText(/rerank_score/)).toBeInTheDocument();
    expect(screen.getByText(/boosts/)).toBeInTheDocument();
    expect(screen.getByText(/final_score/)).toBeInTheDocument();
  });
});
