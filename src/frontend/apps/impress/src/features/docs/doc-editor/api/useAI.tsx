import { useMutation } from '@tanstack/react-query';

import { APIError, errorCauses, fetchAPI } from '@/api';

export type AIActions =
  | 'prompt'
  | 'rephrase'
  | 'summarize'
  | 'translate'
  | 'correct'
  | 'translate_fr'
  | 'translate_en'
  | 'translate_de';

export type AIParams = {
  text: string;
  action: AIActions;
};

export type AIResponse = {
  answer: string;
};

export const AI = async ({ ...params }: AIParams): Promise<AIResponse> => {
  const response = await fetchAPI(`ai/`, {
    method: 'POST',
    body: JSON.stringify({
      ...params,
    }),
  });

  if (!response.ok) {
    throw new APIError('Failed to request ai', await errorCauses(response));
  }

  return response.json() as Promise<AIResponse>;
};

export function useAI() {
  return useMutation<AIResponse, APIError, AIParams>({
    mutationFn: AI,
  });
}
