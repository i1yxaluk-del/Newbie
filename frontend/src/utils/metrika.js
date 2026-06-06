const COUNTER_ID = process.env.REACT_APP_YM_COUNTER_ID || "109692310";

export function reachGoal(goal, params) {
  if (typeof window !== "undefined" && window.ym) {
    window.ym(COUNTER_ID, "reachGoal", goal, params);
  }
}
