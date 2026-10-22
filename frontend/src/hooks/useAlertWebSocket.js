import { useEffect, useRef } from 'react'
import { Client } from '@stomp/stompjs'

/**
 * Subscribes to /topic/alerts over STOMP/WebSocket.
 * onAlert(alert) is called for each incoming alert — no re-subscribe on re-render.
 */
export function useAlertWebSocket(onAlert, onConnect) {
  const callbackRef = useRef(onAlert)
  const connectRef  = useRef(onConnect)
  useEffect(() => { callbackRef.current = onAlert },   [onAlert])
  useEffect(() => { connectRef.current  = onConnect }, [onConnect])

  useEffect(() => {
    const wsProto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const client = new Client({
      brokerURL: `${wsProto}//${window.location.host}/ws`,
      reconnectDelay: 5000,
      onConnect: () => {
        if (connectRef.current) connectRef.current()
        client.subscribe('/topic/alerts', (msg) => {
          try { callbackRef.current(JSON.parse(msg.body)) } catch {}
        })
      },
      onStompError: (frame) => {
        console.warn('STOMP error', frame.headers?.message)
      },
    })
    client.activate()
    return () => client.deactivate()
  }, [])
}
