/**
 * Tipos TypeScript para el sistema de reconocimiento de gestos
 */

export enum GestureType {
  UNKNOWN = "unknown",
  OPEN_PALM = "open_palm",
  CLOSED_FIST = "closed_fist",
  THUMBS_UP = "thumbs_up",
  THUMBS_DOWN = "thumbs_down",
  PINCH = "pinch",
  VICTORY = "victory",
  OK_SIGN = "ok_sign",
  POINTING = "pointing",
}

export interface HandLandmark {
  x: number;
  y: number;
}

export interface HandLandmarks {
  wrist: [number, number];
  thumb_tip: [number, number];
  index_tip: [number, number];
  middle_tip: [number, number];
  ring_tip: [number, number];
  pinky_tip: [number, number];
}

export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface GestureData {
  gesture: GestureType;
  confidence: number;
  handedness: "Left" | "Right";
  bounding_box: [number, number, number, number]; // [x, y, w, h]
  landmarks: HandLandmarks;
}

export interface GestureUpdate {
  type: "gesture_update";
  timestamp: string;
  gestures: GestureData[];
  fps: number;
}

export interface StatsData {
  total_frames: number;
  total_gestures_detected: number;
  gestures_count: Record<string, number>;
  fps: number;
  uptime: number;
  start_time: number | null;
}

export interface WebSocketMessage {
  type: "connected" | "gesture_update" | "stats" | "error";
  message?: string;
  data?: GestureUpdate | StatsData;
  timestamp?: string;
}

export interface ConnectionStatus {
  connected: boolean;
  error?: string;
}
