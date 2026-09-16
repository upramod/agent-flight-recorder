import test from "node:test";
import assert from "node:assert/strict";
import { runMetadataErrorStudy } from "../dist/metadataErrorStudy.js";

test("sensitivity downgrade study exposes trusted-label dependency", () => {
  const result = runMetadataErrorStudy(20, 7, [0, 1]);
  const clean = result.labelErrors.filter(row => row.probability === 0);
  const corrupt = result.labelErrors.filter(row => row.probability === 1);

  assert.equal(clean.length, 3);
  assert.ok(clean.every(row => row.unsafeExecuted === 0));
  assert.equal(corrupt.length, 3);
  assert.ok(corrupt.every(row =>
    row.corruptedTrials === 20 && row.unsafeExecutionRate === 1
  ));
});

test("invalid lineage fails closed but combined lineage and label loss does not", () => {
  const result = runMetadataErrorStudy(1, 1, [0]);
  const byError = Object.fromEntries(
    result.structuralErrors.map(row => [row.error, row])
  );

  assert.equal(byError.producer_lineage_omitted.unsafeExecuted, 0);
  assert.equal(byError.wrong_input_reference.unsafeExecuted, 0);
  assert.equal(byError.all_lineage_omitted.unsafeExecuted, 0);
  assert.equal(byError.lineage_and_label_omitted.unsafeExecuted, 1);
});
