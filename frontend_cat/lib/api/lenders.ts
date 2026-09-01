import { apiPost } from "./client";
import type { BorrowerProfile, MatchResponse } from "./types";

export function matchLenders(profile: BorrowerProfile): Promise<MatchResponse> {
  return apiPost<MatchResponse, BorrowerProfile>("/api/v1/lenders/match", profile);
}
