import { useEffect, useRef, useState } from 'react';
import { sendGreenhouseMessage } from '../services/api.js';

const MAX_MESSAGES = 30;
const REQUEST_TIMEOUT_MS = 130_000;

export default function ChatBox() {
  const [draft, setDraft] = useState('');
  const [messages, setMessages] = useState([]);
  const [pendingId, setPendingId] = useState(null);
  const requestRef = useRef(null);
  const nextId = useRef(0);
  const logRef = useRef(null);
  const followOutput = useRef(true);

  useEffect(() => () => requestRef.current?.abort(), []);
  useEffect(() => {
    if (followOutput.current && logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [messages]);

  async function ask(question, retryId) {
    if (requestRef.current || !question.trim() || question.length > 2000) return;
    const id = retryId ?? ++nextId.current;
    const controller = new AbortController();
    requestRef.current = controller;
    setPendingId(id);
    followOutput.current = true;
    if (retryId) {
      setMessages((previous) => previous.map((message) => message.id === id
        ? { ...message, status: 'pending', error: null } : message));
    } else {
      setMessages((previous) => [...previous, { id, question, status: 'pending' }].slice(-MAX_MESSAGES));
      setDraft('');
    }

    let timedOut = false;
    const timer = setTimeout(() => { timedOut = true; controller.abort(); }, REQUEST_TIMEOUT_MS);
    try {
      const response = await sendGreenhouseMessage(question, 'en', { signal: controller.signal });
      if (controller.signal.aborted) return;
      setMessages((previous) => previous.map((message) => message.id === id
        ? { ...message, status: 'success', answer: response.reply, contextUsed: response.context_used } : message));
    } catch (error) {
      if (controller.signal.aborted && !timedOut) return;
      setMessages((previous) => previous.map((message) => message.id === id ? {
        ...message,
        status: 'error',
        error: timedOut ? 'The assistant took too long to respond. Please try again.'
          : error instanceof TypeError ? 'Unable to reach the assistant. Check your connection and try again.'
            : error.status === 503 ? 'The assistant is temporarily unavailable. Please try again later.'
            : error.message || 'The assistant could not reply. Please try again.',
      } : message));
    } finally {
      clearTimeout(timer);
      requestRef.current = null;
      if (!controller.signal.aborted || timedOut) setPendingId(null);
    }
  }

  return (
    <section className="chat-box assistant-panel" aria-labelledby="chat-title">
      <h2 id="chat-title">
        <svg viewBox="0 0 32 32" aria-hidden="true"><path d="M28 15c0 7-6 12-13 12-2 0-4-.5-6-1L3 29l2-7a11 11 0 0 1-3-7C2 8 8 3 15 3s13 5 13 12Z" /></svg>
        Ask the Greenhouse Assistant
      </h2>
      <div className="chat-box__messages" ref={logRef} role="log" aria-label="Greenhouse conversation" aria-live="polite" onScroll={(event) => {
        const log = event.currentTarget;
        followOutput.current = log.scrollHeight - log.scrollTop - log.clientHeight < 40;
      }}>
        {messages.length === 0 && <p className="assistant-panel__empty">Ask about your greenhouse conditions and sensor readings.</p>}
        {messages.map((message) => (
          <div className="chat-box__exchange" key={message.id}>
            <div className="chat-box__message chat-box__message--user"><span className="chat-box__speaker">You</span><p>{message.question}</p></div>
            <div className="chat-box__message chat-box__message--assistant" aria-busy={message.status === 'pending'}>
              <span className="chat-box__speaker">Assistant</span>
              {message.status === 'pending' ? <p>Thinking… This may take a moment.</p>
                : message.status === 'error' ? <><p className="chat-box__error">{message.error}</p><button type="button" className="chat-box__retry" disabled={pendingId !== null} onClick={() => ask(message.question, message.id)}>Retry</button></>
                  : <><p>{message.answer}</p>{message.contextUsed?.latest_reading === false && <p className="assistant-panel__note">No latest sensor reading was available for this answer.</p>}</>}
            </div>
          </div>
        ))}
      </div>
      <form className="chat-box__form" onSubmit={(event) => { event.preventDefault(); ask(draft.trim()); }}>
        <label htmlFor="chat-question">Your question</label>
        <div className="chat-box__input-row">
          <textarea id="chat-question" rows="2" maxLength={2000} value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="Ask about your greenhouse…" aria-describedby="chat-help" />
          <button type="submit" disabled={!draft.trim() || pendingId !== null}>{pendingId !== null ? 'Sending…' : 'Send'}</button>
        </div>
        <p id="chat-help" className="assistant-panel__note">{draft.length}/2,000 characters · Questions use greenhouse readings; earlier messages are not sent.</p>
      </form>
    </section>
  );
}
