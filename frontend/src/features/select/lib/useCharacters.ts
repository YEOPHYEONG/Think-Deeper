import data from "../data/characters.json" assert { type: "json" };
import type { CharacterMeta } from "../types";

/**
 *  캐릭터 메타데이터 배열을 반환하는 간단한 훅
 */
export const useCharacters = (): CharacterMeta[] => {
  return data as CharacterMeta[];
};
