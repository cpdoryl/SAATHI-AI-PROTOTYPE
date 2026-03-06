/**
 * SAATHI AI — Razorpay Payment Flow Component
 * Handles appointment payment checkout with Razorpay SDK.
 */
import React, { useState } from 'react'
import { createPaymentOrder, verifyPayment } from '@/lib/api'

interface PaymentFlowProps {
  appointmentId: string
  amountInr: number
  clinicianName: string
  scheduledAt: string
  onSuccess: (paymentId: string) => void
  onFailure: (error: string) => void
}

export function PaymentFlow({ appointmentId, amountInr, clinicianName, scheduledAt, onSuccess, onFailure }: PaymentFlowProps) {
  const [loading, setLoading] = useState(false)

  const handlePayment = async () => {
    setLoading(true)
    try {
      const { data: order } = await createPaymentOrder({ appointment_id: appointmentId, amount_inr: amountInr })

      // Load Razorpay SDK dynamically
      const Razorpay = (window as any).Razorpay
      if (!Razorpay) {
        throw new Error('Razorpay SDK not loaded. Add <script src="https://checkout.razorpay.com/v1/checkout.js"> to index.html')
      }

      const rzp = new Razorpay({
        key: order.key_id,
        amount: order.amount_paise,
        currency: 'INR',
        name: 'Saathi AI Therapy',
        description: `Session with ${clinicianName} on ${new Date(scheduledAt).toLocaleDateString()}`,
        order_id: order.order_id,
        handler: async (response: any) => {
          const { data } = await verifyPayment({
            razorpay_order_id: response.razorpay_order_id,
            razorpay_payment_id: response.razorpay_payment_id,
            razorpay_signature: response.razorpay_signature,
          })
          if (data.verified) {
            onSuccess(response.razorpay_payment_id)
          } else {
            onFailure('Payment verification failed')
          }
        },
        prefill: {},
        theme: { color: '#4F46E5' },
      })

      rzp.open()
    } catch (err: any) {
      onFailure(err.message || 'Payment failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border p-6 max-w-md mx-auto">
      <h2 className="text-xl font-bold text-gray-900 mb-4">Complete Booking</h2>
      <div className="space-y-3 mb-6">
        <div className="flex justify-between text-sm">
          <span className="text-gray-500">Clinician</span>
          <span className="font-medium">{clinicianName}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-gray-500">Date & Time</span>
          <span className="font-medium">{new Date(scheduledAt).toLocaleString()}</span>
        </div>
        <div className="flex justify-between text-sm border-t pt-3">
          <span className="font-semibold text-gray-800">Total</span>
          <span className="font-bold text-indigo-600">₹{amountInr}</span>
        </div>
      </div>
      <button
        onClick={handlePayment}
        disabled={loading}
        className="w-full bg-indigo-600 text-white py-3 rounded-lg font-semibold hover:bg-indigo-700 disabled:opacity-50 transition-colors"
      >
        {loading ? 'Processing...' : `Pay ₹${amountInr}`}
      </button>
    </div>
  )
}
