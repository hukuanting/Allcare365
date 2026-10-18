import { vi } from 'vitest';
vi.mock('react-router-dom', () => ({
  useSearchParams: () => [new URLSearchParams()],
}));

import {
  snapshotDisplayValue,
  modelReferenceUrl,
  filterRiskResults,
  groupRiskResults,
  normalizePendingModels,
  normalizeRiskResults,
  resolveRiskSection,
} from './RiskAnalysis';

describe('risk analysis clinical-system grouping', () => {
  test('prefers the stable backend clinical_system over algorithm fallback', () => {
    expect(resolveRiskSection({
      clinical_system: 'respiratory',
      category: 'diabetes',
      algorithm: 'framingham_diabetes',
    })).toBe('respiratory');

    expect(resolveRiskSection({
      clinical_system: { coding: [{ code: 'renal', display: 'Renal' }] },
      algorithm: 'aha_prevent_cvd_10y',
    })).toBe('renal');
  });

  test('understands backend category and system aliases', () => {
    expect(resolveRiskSection({ category: 'liver_fibrosis' })).toBe('hepatic');
    expect(resolveRiskSection({ system: 'metabolic_endocrine' })).toBe('metabolic_endocrine');
    expect(resolveRiskSection({ category: 'lung_cancer' })).toBe('respiratory');
    expect(resolveRiskSection({ category: 'cardiovascular_diabetes' })).toBe('cardiovascular');
  });

  test.each([
    ['caide_dementia_20y', 'dementia_20_year_risk_score', 'neurocognitive'],
    ['aha_prevent_hf_10y', 'heart_failure_10_year_risk', 'cardiovascular'],
    ['nafld_fibrosis', 'fatty_liver_risk', 'hepatic'],
    ['bmi', 'body_mass_index', 'metabolic_endocrine'],
    ['future_ckd_model', 'chronic_kidney_disease', 'renal'],
    ['future_gad_model', 'anxiety_severity', 'mental_health'],
    ['future_unknown_model', 'unclassified_result', 'other'],
  ])('deterministically maps %s / %s to %s', (algorithm, outcome, expected) => {
    expect(resolveRiskSection({ algorithm, outcome })).toBe(expected);
  });

  test('groups every normalized result exactly once without dropping clinical details', () => {
    const cards = normalizeRiskResults({
      disease_risk_results: [
        {
          id: 'diabetes-result',
          algorithm: 'framingham_diabetes',
          display_name: 'Framingham 糖尿病風險',
          display_name_zh: 'Framingham 糖尿病風險',
          display_name_en: 'Framingham Diabetes Risk',
          outcome_label: '糖尿病風險',
          missing_data_labels: ['空腹血糖'],
          limitations: ['僅適用於指定年齡範圍'],
          recommendation_text: '補齊資料後重新評估',
          requires_doctor_review: true,
        },
        {
          id: 'renal-result',
          clinical_system: 'renal',
          algorithm: 'future_renal_model',
          outcome: 'kidney_risk',
          risk_percentage: '12%',
          risk_level: 'moderate',
        },
        {
          id: 'other-result',
          algorithm: 'future_unknown_model',
          outcome: 'unclassified_result',
          risk_percentage: '4%',
          risk_level: 'low',
        },
      ],
    });

    expect(cards).toHaveLength(3);
    expect(cards[0]).toEqual(expect.objectContaining({
      title: 'Framingham 糖尿病風險',
      titleEn: 'Framingham Diabetes Risk',
      sectionKey: 'metabolic_endocrine',
      missing: ['空腹血糖'],
      limitations: ['僅適用於指定年齡範圍'],
      recommendation: '補齊資料後重新評估',
      review: true,
    }));

    const groups = groupRiskResults(cards);
    const groupedCards = groups.flatMap((group) => group.cards);

    expect(groups.map((group) => group.key)).toEqual(['renal', 'metabolic_endocrine', 'other']);
    expect(groupedCards).toHaveLength(cards.length);
    expect(groupedCards.map((card) => card.id).sort()).toEqual(cards.map((card) => card.id).sort());
  });

  test('separates patient calculations from the model-onboarding catalog', () => {
    const payload = {
      disease_risk_results: [
        {
          id: 'runtime-result',
          algorithm: 'framingham_diabetes',
          display_name: 'Framingham Diabetes Risk',
          outcome: 'diabetes_risk',
          risk_percentage: '8%',
          risk_level: 'moderate',
          clinical_system: 'metabolic_endocrine',
        },
      ],
      algorithm_catalog: {
        systems: [
          {
            code: 'metabolic_endocrine',
            algorithms: [
              {
                catalog_kind: 'runtime',
                algorithm_id: 'framingham_diabetes',
                display_name: 'Framingham Diabetes Risk',
                outcome_key: 'diabetes_risk',
                governance_status: 'runtime_approved',
                runtime_enabled: true,
              },
              {
                catalog_kind: 'review_candidate',
                algorithm_id: 'tyg_index',
                display_name: 'Triglyceride-Glucose Index (TyG)',
                target: 'Surrogate insulin-resistance index',
                governance_status: 'clinical_review_required',
                runtime_enabled: false,
                issues: ['Population thresholds require local validation.'],
              },
            ],
          },
          {
            code: 'respiratory',
            algorithms: [
              {
                catalog_kind: 'review_candidate',
                algorithm_id: 'mayo_pulmonary_nodule',
                display_name: 'Mayo Pulmonary Nodule',
                governance_status: 'clinical_review_required',
                runtime_enabled: false,
              },
            ],
          },
        ],
      },
    };
    const cards = normalizeRiskResults(payload);
    const pending = normalizePendingModels(payload);

    expect(cards).toHaveLength(1);
    expect(cards.filter((card) => card.algorithm === 'framingham_diabetes')).toHaveLength(1);
    expect(cards.find((card) => card.algorithm === 'framingham_diabetes')).toEqual(
      expect.objectContaining({ value: '8%', catalogOnly: false }),
    );
    expect(pending).toHaveLength(2);
    expect(pending.find((card) => card.algorithm === 'tyg_index')).toEqual(
      expect.objectContaining({
        value: '模型準備中',
        level: 'review_required',
        sectionKey: 'metabolic_endocrine',
        catalogOnly: true,
      }),
    );
    expect(pending.find((card) => card.algorithm === 'mayo_pulmonary_nodule').sectionKey).toBe('respiratory');
  });
});


describe('risk result filtering', () => {
  const cards = [
    { algorithm: 'nelson', title: '腎臟風險', titleEn: 'Nelson', item: '五年風險', level: 'high', applicability: 'applicable' },
    { algorithm: 'prisq', title: '篩檢', titleEn: 'PRISQ', level: 'missing', applicability: 'applicable' },
    { algorithm: 'gail', title: '乳癌', titleEn: 'Gail', level: 'not_applicable', applicability: 'not_applicable' },
  ];
  test('combines bilingual text with status without changing the source', () => {
    expect(filterRiskResults(cards, ' NELSON ', 'attention')).toEqual([cards[0]]);
    expect(filterRiskResults(cards, '腎臟', 'missing')).toEqual([]);
    expect(filterRiskResults(cards, '', 'missing')).toEqual([cards[1]]);
    expect(filterRiskResults(cards, '', 'not_applicable')).toEqual([cards[2]]);
    expect(cards).toHaveLength(3);
  });
});


test('preserves model provenance and allows only ordinary web reference links', () => {
  expect(modelReferenceUrl('javascript:alert(1)')).toBeNull();
  expect(modelReferenceUrl('https://user:password@example.org/paper')).toBeNull();
  expect(modelReferenceUrl('https://doi.org/10.1111/jdi.13445')).toBe('https://doi.org/10.1111/jdi.13445');
  const [card] = normalizeRiskResults({disease_risk_results:[{
    algorithm:'prisq_prediabetes_screen', model_version:'expert-source-2026-10-10',
    method_uri:'https://doi.org/10.1111/jdi.13445', risk_level:'informational',
    evidence:{source_document:'Abbas 2021 Table 2', time_horizon:null},
  }]});
  expect(card.sourceDocument).toBe('Abbas 2021 Table 2');
  expect(card.modelVersion).toBe('expert-source-2026-10-10');
  expect(card.levelLabel).toBe('參考指標');
});


test('input snapshot uses specific assay units and preserves unknown versus false', () => {
 expect(snapshotDisplayValue('ferritin',300)).toBe('300 ng/mL');
 expect(snapshotDisplayValue('h_pylori_igg_eiu',34)).toBe('34 EIU');
 expect(snapshotDisplayValue('diabetes_medication','oral')).toBe('口服藥');
 expect(snapshotDisplayValue('regular_fried_food',false)).toBe('否');
 expect(snapshotDisplayValue('ferritin',null)).toBe('無資料');
});
