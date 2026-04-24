import { useQuery } from '@tanstack/react-query';
import { metricsApi } from '../api/client';

export function useCITADELStats() {
  return useQuery({
    queryKey: ['CITADEL-stats'],
    queryFn: metricsApi.summary,
  });
}
