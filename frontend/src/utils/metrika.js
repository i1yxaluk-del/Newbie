// CRA подставляет REACT_APP_* во время сборки, не при старте уже готового сайта.
const COUNTER_ID = process.env.REACT_APP_YM_COUNTER_ID || "109692310";

export function reachGoal(goal, params) {
  // Отсутствие счётчика не мешает приложению. params не должны содержать ПДн/секреты;
  // событие формы означает действие пользователя, а не продажу или оплату.
  if (typeof window !== "undefined" && window.ym) {
    window.ym(COUNTER_ID, "reachGoal", goal, params);
  }
}
