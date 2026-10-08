import { Route, Routes } from 'react-router'
import { RequireAuth } from './auth/RequireAuth'
import { AppShell } from './components/AppShell'
import { ShopLayout } from './components/shop/ShopLayout'
import { AdminDocumentsPage } from './pages/AdminDocumentsPage'
import { AdminMetricsPage } from './pages/AdminMetricsPage'
import { LoginPage, RegisterPage } from './pages/AuthPages'
import { ChatPage } from './pages/ChatPage'
import { DashboardPage } from './pages/DashboardPage'
import { NotFoundPage } from './pages/NotFoundPage'
import { OrderDetailPage, OrdersPage } from './pages/OrdersPage'
import { ProfilePage } from './pages/ProfilePage'
import { CartPage } from './pages/shop/CartPage'
import { CheckoutPage } from './pages/shop/CheckoutPage'
import { HomePage } from './pages/shop/HomePage'
import { PayPage } from './pages/shop/PayPage'
import { ProductPage } from './pages/shop/ProductPage'
import { ShopPage } from './pages/shop/ShopPage'
import { TicketDetailPage, TicketsPage } from './pages/TicketsPage'

export function App() {
  return (
    <Routes>
      {/* The shop: open to everyone, checkout needs an account. */}
      <Route element={<ShopLayout />}>
        <Route index element={<HomePage />} />
        <Route path="/shop" element={<ShopPage />} />
        <Route path="/product/:slug" element={<ProductPage />} />
        <Route path="/cart" element={<CartPage />} />
        <Route
          path="/checkout"
          element={
            <RequireAuth>
              <CheckoutPage />
            </RequireAuth>
          }
        />
        <Route path="*" element={<NotFoundPage />} />
      </Route>

      {/* The simulated payment provider has its own, bank-like page. */}
      <Route
        path="/pay/:paymentId"
        element={
          <RequireAuth>
            <PayPage />
          </RequireAuth>
        }
      />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      {/* Your account and support (and the admin pages for staff). */}
      <Route
        element={
          <RequireAuth>
            <AppShell />
          </RequireAuth>
        }
      >
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route
          path="/chat/:conversationId?"
          element={
            <RequireAuth roles={['CUSTOMER']}>
              <ChatPage />
            </RequireAuth>
          }
        />
        <Route path="/orders" element={<OrdersPage />} />
        <Route path="/orders/:orderId" element={<OrderDetailPage />} />
        <Route path="/tickets" element={<TicketsPage />} />
        <Route path="/tickets/:ticketId" element={<TicketDetailPage />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route
          path="/admin/documents"
          element={
            <RequireAuth roles={['ADMIN']}>
              <AdminDocumentsPage />
            </RequireAuth>
          }
        />
        <Route
          path="/admin/metrics"
          element={
            <RequireAuth roles={['ADMIN']}>
              <AdminMetricsPage />
            </RequireAuth>
          }
        />
      </Route>
    </Routes>
  )
}
