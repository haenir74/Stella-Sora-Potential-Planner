export interface BuildData {
  build_name: string;
  characters: Record<string, Record<string, number>>;
}

export interface PotentialLevelMap {
  [potentialId: number]: number;
}

export interface MarkPriorityMap {
  [potentialId: number]: number;
}

export interface ParsedCharacter {
  char_id: number;
  mapped_char_idx: number;
  potentials: number[];
  mapped_potentials: number[];
  potential_levels: PotentialLevelMap;
  marks: MarkPriorityMap;
}

export interface DecodeResult {
  build_name?: string;
  raw_characters?: Record<string, ParsedCharacter>;
  version?: number;
  error?: string;
}
