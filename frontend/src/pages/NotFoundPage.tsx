import { SearchX } from 'lucide-react'
import { PageContainer } from '../components/AppShell'
import { EmptyState } from '../components/feedback'
import { ButtonLink } from '../components/ui'

export function NotFoundPage() {
  return (
    <PageContainer>
      <EmptyState icon={SearchX} title="Page not found" action={<ButtonLink to="/dashboard">Go to the dashboard</ButtonLink>}>
        The page you're looking for doesn't exist or you don't have access to it.
      </EmptyState>
    </PageContainer>
  )
}
