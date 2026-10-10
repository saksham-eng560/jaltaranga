import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import Ajv2020 from 'ajv/dist/2020';
import type { AnySchema } from 'ajv';
import addFormats from 'ajv-formats';
import { describe, expect, it } from 'vitest';

const repo = resolve(process.cwd(), '..');
const read = (path: string) => JSON.parse(readFileSync(resolve(repo, path), 'utf8')) as unknown;
const ajv = new Ajv2020({ allErrors: true, strict: false });
addFormats(ajv);
const schema = (name: string) => ajv.compile(read(`shared/schemas/${name}.schema.json`) as AnySchema);

describe('shared contract fixtures', () => {
  it('validates the manifest adapter against the shared schema', () => {
    expect(schema('manifest')(read('frontend/public/fixtures/manifest.json'))).toBe(true);
  });

  it('validates evacuation plans, road state, shelter and forecast records', () => {
    const plans = read('shared/fixtures/evacuation_plans.json') as Record<string, unknown[]>;
    const planValidator = schema('evacuation_plan');
    Object.values(plans).flat().forEach((item) => expect(planValidator(item), JSON.stringify(planValidator.errors)).toBe(true));
    const roadValidator = schema('road_segment_status');
    (read('shared/fixtures/road_segment_status.json') as unknown[]).forEach((item) => expect(roadValidator(item), JSON.stringify(roadValidator.errors)).toBe(true));
    const shelterValidator = schema('shelter');
    (read('shared/fixtures/shelters.json') as unknown[]).forEach((item) => expect(shelterValidator(item), JSON.stringify(shelterValidator.errors)).toBe(true));
    const forecastValidator = schema('forecast_node');
    (read('shared/fixtures/forecast_nodes.json') as unknown[]).forEach((item) => expect(forecastValidator(item), JSON.stringify(forecastValidator.errors)).toBe(true));
  });

  it('validates dispatch, unreachable and field-report responses', () => {
    const dispatchValidator = schema('dispatch_card');
    for (const file of ['dispatch_card.json', 'dispatch_card_fallback.json', 'dispatch_card_shelter_in_place.json']) {
      expect(dispatchValidator(read(`shared/fixtures/${file}`)), JSON.stringify(dispatchValidator.errors)).toBe(true);
    }
    const unreachableValidator = schema('unreachable_entry');
    (read('shared/fixtures/plans_unreachable.json') as unknown[]).forEach((item) => expect(unreachableValidator(item), JSON.stringify(unreachableValidator.errors)).toBe(true));
    const reportValidator = schema('report_post_response');
    expect(reportValidator(read('shared/fixtures/report_post_response.json')), JSON.stringify(reportValidator.errors)).toBe(true);
  });
});

