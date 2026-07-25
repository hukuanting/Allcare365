jest.mock('react-router-dom', () => ({
  useSearchParams: () => [new URLSearchParams()],
}), { virtual: true });

import {
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
        value: '待臨床審核',
        level: 'review_required',
        sectionKey: 'metabolic_endocrine',
        catalogOnly: true,
      }),
    );
    expect(pending.find((card) => card.algorithm === 'mayo_pulmonary_nodule').sectionKey).toBe('respiratory');
  });
});
