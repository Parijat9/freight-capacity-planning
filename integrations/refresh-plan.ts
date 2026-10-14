interface PlanRow { lane_id: string; expected_loads: number; contracted_loads: number; }

function main(workbook: ExcelScript.Workbook, planJson: string): string {
  const incoming: PlanRow[] = JSON.parse(planJson);
  if (!Array.isArray(incoming)) throw new Error("Expected a plan array");
  const table = workbook.getTable("CapacityPlan");
  const range = table.getRangeBetweenHeaderAndTotal();
  const rows = range.getValues();
  const indexed: { [key: string]: PlanRow } = {};
  for (const item of incoming) {
    if (indexed[item.lane_id]) throw new Error("Duplicate lane: " + item.lane_id);
    if (!Number.isFinite(item.expected_loads) || item.expected_loads < 0 ||
        !Number.isInteger(item.contracted_loads) || item.contracted_loads < 0) {
      throw new Error("Invalid capacity for " + item.lane_id);
    }
    indexed[item.lane_id] = item;
  }
  if (incoming.length !== rows.length) throw new Error("Lane coverage mismatch");
  const updates: number[][] = rows.map(row => {
    const item = indexed[String(row[0])];
    if (!item) throw new Error("Missing lane: " + row[0]);
    return [Math.ceil(item.expected_loads), item.contracted_loads];
  });
  range.getCell(0, 1).getResizedRange(rows.length - 1, 1).setValues(updates);
  workbook.getApplication().calculate(ExcelScript.CalculationType.full);
  return "Updated " + rows.length + " lanes";
}
