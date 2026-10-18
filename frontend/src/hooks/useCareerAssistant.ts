import { useCallback, useRef, useState } from 'react';
import { postChatMessage } from '../api/careerAssistantApi';
import { ApiError } from '../types/chat';
import type { AssistantStatus, ChatMessage } from '../types/chat';
import { suggestedQuestions } from '../data/suggestedQuestions';

const UNAVAILABLE_MESSAGE =
  'The AI assistant is temporarily unavailable. You can still explore Abhishek’s experience and contact details on this page.';

export const INITIAL_ASSISTANT_MESSAGE =
  'Hi! I’m Abhishek’s AI career assistant. Ask me about his professional experience, AI/ML projects, technical skills, education, or career background.';

function createId(prefix: string): string {
  return `${prefix}-${Math.random().toString(36).slice(2, 10)}`;
}

function createSessionId(): string {
  const webCrypto = globalThis.crypto;
  if (webCrypto && typeof webCrypto.randomUUID === 'function') {
    return webCrypto.randomUUID();
  }
  return createId('session');
}

export interface CareerAssistantState {
  messages: ChatMessage[];
  status: AssistantStatus;
  errorMessage: string | null;
  followUpQuestions: string[];
  showSuggestions: boolean;
  askQuestion: (question: string) => Promise<void>;
}

export function useCareerAssistant(): CareerAssistantState {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'assistant-welcome',
      role: 'assistant',
      text: INITIAL_ASSISTANT_MESSAGE,
      abstained: false,
    },
  ]);
  const [status, setStatus] = useState<AssistantStatus>('idle');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [followUpQuestions, setFollowUpQuestions] = useState<string[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(true);

  const sessionIdRef = useRef<string | null>(null);
  const inFlightRef = useRef(false);

  const askQuestion = useCallback(async (question: string) => {
    const trimmed = question.trim();
    if (!trimmed || inFlightRef.current) return;

    inFlightRef.current = true;
    sessionIdRef.current ??= createSessionId();

    setShowSuggestions(false);
    setFollowUpQuestions([]);
    setErrorMessage(null);
    setStatus('loading');
    setMessages((previous) => [
      ...previous,
      { id: createId('user'), role: 'user', text: trimmed, abstained: false },
    ]);

    try {
      const response = await postChatMessage({
        message: trimmed,
        session_id: sessionIdRef.current,
      });

      setMessages((previous) => [
        ...previous,
        {
          id: createId('assistant'),
          role: 'assistant',
          text: response.answer,
          abstained: response.abstained,
        },
      ]);
      setFollowUpQuestions(response.suggested_questions);
      setStatus('idle');
    } catch (error) {
      const message =
        error instanceof ApiError && error.kind === 'invalid' ? error.message : UNAVAILABLE_MESSAGE;
      setErrorMessage(message);
      setStatus('error');
    } finally {
      inFlightRef.current = false;
    }
  }, []);

  return {
    messages,
    status,
    errorMessage,
    followUpQuestions,
    showSuggestions,
    askQuestion,
  };
}

export const initialSuggestions = suggestedQuestions;
