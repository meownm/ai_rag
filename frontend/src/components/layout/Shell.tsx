import { PropsWithChildren } from 'react';
import { TopNav } from './TopNav';
import { SideNav } from './SideNav';
import { ErrorBoundary } from './ErrorBoundary';

export function Shell({ children }: PropsWithChildren) {
  return (
    <ErrorBoundary>
      <div className="h-screen">
        <TopNav />
        <div className="flex h-[calc(100vh-56px)]">
          <SideNav />
          <main className="flex-1 overflow-auto p-4">{children}</main>
        </div>
      </div>
    </ErrorBoundary>
  );
}
