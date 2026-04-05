<script lang="ts">
	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	dayjs.extend(relativeTime);

	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';
	const i18n = getContext('i18n');

	import { WEBUI_NAME } from '$lib/stores';
	import { getEvalJobs, createEvalJob, cancelEvalJob, type EvalJob } from '$lib/apis/evaluations/jobs';
	import { getModels } from '$lib/apis/index';

	import Spinner from '../common/Spinner.svelte';
	import Tooltip from '../common/Tooltip.svelte';

	const getToken = () => localStorage.getItem('token') ?? '';

	let loaded = false;
	let submitting = false;

	let jobs: EvalJob[] = [];
	let modelItems: { value: string; label: string }[] = [];

	type BenchmarkGroup = {
		id: string;
		name: string;
		description: string;
		language: string;
		gated?: boolean;
		tasks: { id: string; name: string; count: number; difficulty: string; category?: string }[];
	};

	// Job submission modal
	let showJobModal = false;
	let activeGroup: BenchmarkGroup | null = null;
	let selectedTasks = new Set<string>();
	let jobModelId = '';
	let modelSearch = '';
	let showModelDropdown = false;
	let jobDryRun = false;

	$: filteredModels = modelSearch
		? modelItems.filter(
				(m) =>
					m.label.toLowerCase().includes(modelSearch.toLowerCase()) ||
					m.value.toLowerCase().includes(modelSearch.toLowerCase())
		  )
		: modelItems;

	// Active eval type for the submission modal
	let activeEvalType: 'bigcode' | 'lm-eval' = 'bigcode';

	// BBH subtask definitions (shared between zero-shot and few-shot)
	const bbhSubtasks = [
		{ name: 'Boolean Expressions', key: 'boolean_expressions', count: 250, difficulty: 'Medium' },
		{ name: 'Causal Judgement', key: 'causal_judgement', count: 187, difficulty: 'Hard' },
		{ name: 'Date Understanding', key: 'date_understanding', count: 250, difficulty: 'Medium' },
		{ name: 'Disambiguation QA', key: 'disambiguation_qa', count: 250, difficulty: 'Medium' },
		{ name: 'Dyck Languages', key: 'dyck_languages', count: 250, difficulty: 'Hard' },
		{ name: 'Formal Fallacies', key: 'formal_fallacies', count: 250, difficulty: 'Hard' },
		{ name: 'Geometric Shapes', key: 'geometric_shapes', count: 250, difficulty: 'Medium' },
		{ name: 'Hyperbaton', key: 'hyperbaton', count: 250, difficulty: 'Medium' },
		{ name: 'Logical Deduction (3 Objects)', key: 'logical_deduction_three_objects', count: 250, difficulty: 'Medium' },
		{ name: 'Logical Deduction (5 Objects)', key: 'logical_deduction_five_objects', count: 250, difficulty: 'Hard' },
		{ name: 'Logical Deduction (7 Objects)', key: 'logical_deduction_seven_objects', count: 250, difficulty: 'Hard' },
		{ name: 'Movie Recommendation', key: 'movie_recommendation', count: 250, difficulty: 'Medium' },
		{ name: 'Multistep Arithmetic', key: 'multistep_arithmetic_two', count: 250, difficulty: 'Hard' },
		{ name: 'Navigate', key: 'navigate', count: 250, difficulty: 'Medium' },
		{ name: 'Object Counting', key: 'object_counting', count: 250, difficulty: 'Medium' },
		{ name: 'Penguins in a Table', key: 'penguins_in_a_table', count: 146, difficulty: 'Hard' },
		{ name: 'Reasoning About Colored Objects', key: 'reasoning_about_colored_objects', count: 250, difficulty: 'Medium' },
		{ name: 'Ruin Names', key: 'ruin_names', count: 250, difficulty: 'Medium' },
		{ name: 'Salient Translation Error Detection', key: 'salient_translation_error_detection', count: 250, difficulty: 'Hard' },
		{ name: 'Snarks', key: 'snarks', count: 178, difficulty: 'Medium' },
		{ name: 'Sports Understanding', key: 'sports_understanding', count: 250, difficulty: 'Medium' },
		{ name: 'Temporal Sequences', key: 'temporal_sequences', count: 250, difficulty: 'Medium' },
		{ name: 'Tracking Shuffled Objects (3)', key: 'tracking_shuffled_objects_three_objects', count: 250, difficulty: 'Medium' },
		{ name: 'Tracking Shuffled Objects (5)', key: 'tracking_shuffled_objects_five_objects', count: 250, difficulty: 'Hard' },
		{ name: 'Tracking Shuffled Objects (7)', key: 'tracking_shuffled_objects_seven_objects', count: 250, difficulty: 'Hard' },
		{ name: 'Web of Lies', key: 'web_of_lies', count: 250, difficulty: 'Medium' },
		{ name: 'Word Sorting', key: 'word_sorting', count: 250, difficulty: 'Medium' }
	];

	// Language & Understanding benchmark cards (lm-eval)
	const leaderboardGroups = [
		{
			id: 'ifeval',
			name: 'IFEval',
			description: 'Instruction-Following Evaluation. Tests a model\'s ability to follow explicit formatting and content constraints.',
			language: 'English',
			tasks: [
				{ id: 'leaderboard_ifeval', name: 'IFEval', count: 541, difficulty: 'Medium' }
			]
		},
		{
			id: 'bbh_cot_zeroshot',
			name: 'BBH (CoT Zero-shot)',
			description: 'BIG-Bench Hard with chain-of-thought zero-shot prompting. 27 challenging tasks spanning logical reasoning, language understanding, and math.',
			language: 'English',
			tasks: bbhSubtasks.map((t) => ({ id: `bbh_cot_zeroshot_${t.key}`, name: t.name, count: t.count, difficulty: t.difficulty }))
		},
		{
			id: 'bbh_cot_fewshot',
			name: 'BBH (CoT Few-shot)',
			description: 'BIG-Bench Hard with chain-of-thought few-shot prompting (3 examples). Same 27 tasks as zero-shot but with in-context examples.',
			language: 'English',
			tasks: bbhSubtasks.map((t) => ({ id: `bbh_cot_fewshot_${t.key}`, name: t.name, count: t.count, difficulty: t.difficulty }))
		},
		{
			id: 'math_hard',
			name: 'MATH Hard',
			description: 'Challenging competition-level mathematics problems (Level 5) requiring multi-step reasoning across 7 math domains.',
			language: 'English',
			tasks: [
				{ id: 'leaderboard_math_algebra_hard', name: 'Algebra', count: 307, difficulty: 'Hard' },
				{ id: 'leaderboard_math_counting_and_prob_hard', name: 'Counting & Probability', count: 123, difficulty: 'Hard' },
				{ id: 'leaderboard_math_geometry_hard', name: 'Geometry', count: 132, difficulty: 'Hard' },
				{ id: 'leaderboard_math_intermediate_algebra_hard', name: 'Intermediate Algebra', count: 280, difficulty: 'Hard' },
				{ id: 'leaderboard_math_num_theory_hard', name: 'Number Theory', count: 154, difficulty: 'Hard' },
				{ id: 'leaderboard_math_prealgebra_hard', name: 'Prealgebra', count: 193, difficulty: 'Hard' },
				{ id: 'leaderboard_math_precalculus_hard', name: 'Precalculus', count: 135, difficulty: 'Hard' }
			]
		},
		{
			id: 'gpqa',
			name: 'GPQA',
			description: 'Graduate-level Google-Proof Q&A. Expert-crafted questions in biology, physics, and chemistry. Requires HuggingFace authentication.',
			language: 'English',
			gated: true,
			tasks: [
				{ id: 'leaderboard_gpqa_diamond', name: 'Diamond', count: 198, difficulty: 'Hard' },
				{ id: 'leaderboard_gpqa_extended', name: 'Extended', count: 546, difficulty: 'Hard' },
				{ id: 'leaderboard_gpqa_main', name: 'Main', count: 448, difficulty: 'Hard' }
			]
		},
		{
			id: 'musr',
			name: 'MUSR',
			description: 'Multistep Soft Reasoning. Tests complex multi-hop reasoning over natural language narratives.',
			language: 'English',
			tasks: [
				{ id: 'leaderboard_musr_chat_murder_mysteries', name: 'Murder Mysteries', count: 250, difficulty: 'Hard' },
				{ id: 'leaderboard_musr_chat_object_placements', name: 'Object Placements', count: 256, difficulty: 'Hard' },
				{ id: 'leaderboard_musr_chat_team_allocation', name: 'Team Allocation', count: 250, difficulty: 'Hard' }
			]
		},
		{
			id: 'mmlu_pro',
			name: 'MMLU-PRO',
			description: 'Massive Multitask Language Understanding (Professional). Harder MMLU variant with 10 answer choices across 14 categories.',
			language: 'English',
			tasks: [
				{ id: 'mmlu_pro_biology', name: 'Biology', count: 717, difficulty: 'Hard' },
				{ id: 'mmlu_pro_business', name: 'Business', count: 789, difficulty: 'Hard' },
				{ id: 'mmlu_pro_chemistry', name: 'Chemistry', count: 1132, difficulty: 'Hard' },
				{ id: 'mmlu_pro_computer_science', name: 'Computer Science', count: 410, difficulty: 'Hard' },
				{ id: 'mmlu_pro_economics', name: 'Economics', count: 844, difficulty: 'Hard' },
				{ id: 'mmlu_pro_engineering', name: 'Engineering', count: 969, difficulty: 'Hard' },
				{ id: 'mmlu_pro_health', name: 'Health', count: 818, difficulty: 'Hard' },
				{ id: 'mmlu_pro_history', name: 'History', count: 381, difficulty: 'Hard' },
				{ id: 'mmlu_pro_law', name: 'Law', count: 1101, difficulty: 'Hard' },
				{ id: 'mmlu_pro_math', name: 'Math', count: 1351, difficulty: 'Hard' },
				{ id: 'mmlu_pro_other', name: 'Other', count: 924, difficulty: 'Hard' },
				{ id: 'mmlu_pro_philosophy', name: 'Philosophy', count: 499, difficulty: 'Hard' },
				{ id: 'mmlu_pro_physics', name: 'Physics', count: 1299, difficulty: 'Hard' },
				{ id: 'mmlu_pro_psychology', name: 'Psychology', count: 798, difficulty: 'Hard' }
			]
		},
		{
			id: 'arc_challenge',
			name: 'ARC Challenge',
			description: 'AI2 Reasoning Challenge. Grade-school science questions that require reasoning beyond simple retrieval.',
			language: 'English',
			tasks: [
				{ id: 'arc_challenge_chat', name: 'ARC Challenge', count: 1172, difficulty: 'Medium' }
			]
		},
		{
			id: 'hellaswag',
			name: 'HellaSwag',
			description: 'Sentence completion benchmark testing commonsense reasoning about physical situations. Split by WikiHow categories and ActivityNet.',
			language: 'English',
			tasks: [
				// ActivityNet
				{ id: 'hellaswag_chat_activitynet_sports', name: 'Sports & Athletics', count: 1095, difficulty: 'Medium', category: 'ActivityNet' },
				{ id: 'hellaswag_chat_activitynet_home', name: 'Home & Maintenance', count: 476, difficulty: 'Medium', category: 'ActivityNet' },
				{ id: 'hellaswag_chat_activitynet_other', name: 'Other Activities', count: 445, difficulty: 'Medium', category: 'ActivityNet' },
				{ id: 'hellaswag_chat_activitynet_personal_care', name: 'Personal Care', count: 314, difficulty: 'Medium', category: 'ActivityNet' },
				{ id: 'hellaswag_chat_activitynet_music', name: 'Music', count: 301, difficulty: 'Medium', category: 'ActivityNet' },
				{ id: 'hellaswag_chat_activitynet_food', name: 'Food & Cooking', count: 284, difficulty: 'Medium', category: 'ActivityNet' },
				{ id: 'hellaswag_chat_activitynet_water', name: 'Water Activities', count: 263, difficulty: 'Medium', category: 'ActivityNet' },
				{ id: 'hellaswag_chat_activitynet_combat', name: 'Combat & Martial Arts', count: 65, difficulty: 'Medium', category: 'ActivityNet' },
				// WikiHow
				{ id: 'hellaswag_chat_wikihow_personal_care', name: 'Personal Care & Style', count: 2627, difficulty: 'Medium', category: 'WikiHow' },
				{ id: 'hellaswag_chat_wikihow_family_life', name: 'Family Life', count: 980, difficulty: 'Medium', category: 'WikiHow' },
				{ id: 'hellaswag_chat_wikihow_food', name: 'Food & Entertaining', count: 500, difficulty: 'Medium', category: 'WikiHow' },
				{ id: 'hellaswag_chat_wikihow_computers', name: 'Computers & Electronics', count: 454, difficulty: 'Medium', category: 'WikiHow' },
				{ id: 'hellaswag_chat_wikihow_health', name: 'Health', count: 427, difficulty: 'Medium', category: 'WikiHow' },
				{ id: 'hellaswag_chat_wikihow_home_garden', name: 'Home & Garden', count: 390, difficulty: 'Medium', category: 'WikiHow' },
				{ id: 'hellaswag_chat_wikihow_finance', name: 'Finance & Business', count: 265, difficulty: 'Medium', category: 'WikiHow' },
				{ id: 'hellaswag_chat_wikihow_pets', name: 'Pets & Animals', count: 255, difficulty: 'Medium', category: 'WikiHow' },
				{ id: 'hellaswag_chat_wikihow_education', name: 'Education & Communications', count: 201, difficulty: 'Medium', category: 'WikiHow' },
				{ id: 'hellaswag_chat_wikihow_youth', name: 'Youth', count: 161, difficulty: 'Medium', category: 'WikiHow' },
				{ id: 'hellaswag_chat_wikihow_sports', name: 'Sports & Fitness', count: 144, difficulty: 'Medium', category: 'WikiHow' },
				{ id: 'hellaswag_chat_wikihow_relationships', name: 'Relationships', count: 113, difficulty: 'Medium', category: 'WikiHow' },
				{ id: 'hellaswag_chat_wikihow_work', name: 'Work World', count: 86, difficulty: 'Medium', category: 'WikiHow' },
				{ id: 'hellaswag_chat_wikihow_cars', name: 'Cars & Other Vehicles', count: 65, difficulty: 'Medium', category: 'WikiHow' },
				{ id: 'hellaswag_chat_wikihow_travel', name: 'Travel', count: 60, difficulty: 'Medium', category: 'WikiHow' },
				{ id: 'hellaswag_chat_wikihow_holidays', name: 'Holidays & Traditions', count: 38, difficulty: 'Medium', category: 'WikiHow' },
				{ id: 'hellaswag_chat_wikihow_philosophy', name: 'Philosophy & Religion', count: 24, difficulty: 'Medium', category: 'WikiHow' },
				{ id: 'hellaswag_chat_wikihow_other', name: 'Other', count: 9, difficulty: 'Medium', category: 'WikiHow' }
			]
		},
		{
			id: 'mmlu',
			name: 'MMLU',
			description: 'Massive Multitask Language Understanding. 57 subjects across STEM, humanities, social sciences, and other domains.',
			language: 'English',
			tasks: [
				// STEM
				{ id: 'mmlu_abstract_algebra_generative', name: 'Abstract Algebra', count: 100, difficulty: 'Hard', category: 'STEM' },
				{ id: 'mmlu_anatomy_generative', name: 'Anatomy', count: 135, difficulty: 'Medium', category: 'STEM' },
				{ id: 'mmlu_astronomy_generative', name: 'Astronomy', count: 152, difficulty: 'Medium', category: 'STEM' },
				{ id: 'mmlu_college_biology_generative', name: 'College Biology', count: 144, difficulty: 'Medium-Hard', category: 'STEM' },
				{ id: 'mmlu_college_chemistry_generative', name: 'College Chemistry', count: 100, difficulty: 'Hard', category: 'STEM' },
				{ id: 'mmlu_college_computer_science_generative', name: 'College Computer Science', count: 100, difficulty: 'Hard', category: 'STEM' },
				{ id: 'mmlu_college_mathematics_generative', name: 'College Mathematics', count: 100, difficulty: 'Hard', category: 'STEM' },
				{ id: 'mmlu_college_physics_generative', name: 'College Physics', count: 102, difficulty: 'Hard', category: 'STEM' },
				{ id: 'mmlu_computer_security_generative', name: 'Computer Security', count: 100, difficulty: 'Medium', category: 'STEM' },
				{ id: 'mmlu_conceptual_physics_generative', name: 'Conceptual Physics', count: 235, difficulty: 'Medium', category: 'STEM' },
				{ id: 'mmlu_electrical_engineering_generative', name: 'Electrical Engineering', count: 145, difficulty: 'Medium-Hard', category: 'STEM' },
				{ id: 'mmlu_elementary_mathematics_generative', name: 'Elementary Mathematics', count: 378, difficulty: 'Easy-Medium', category: 'STEM' },
				{ id: 'mmlu_high_school_biology_generative', name: 'HS Biology', count: 310, difficulty: 'Medium', category: 'STEM' },
				{ id: 'mmlu_high_school_chemistry_generative', name: 'HS Chemistry', count: 203, difficulty: 'Medium', category: 'STEM' },
				{ id: 'mmlu_high_school_computer_science_generative', name: 'HS Computer Science', count: 100, difficulty: 'Medium', category: 'STEM' },
				{ id: 'mmlu_high_school_mathematics_generative', name: 'HS Mathematics', count: 270, difficulty: 'Medium-Hard', category: 'STEM' },
				{ id: 'mmlu_high_school_physics_generative', name: 'HS Physics', count: 151, difficulty: 'Medium-Hard', category: 'STEM' },
				{ id: 'mmlu_high_school_statistics_generative', name: 'HS Statistics', count: 216, difficulty: 'Medium', category: 'STEM' },
				{ id: 'mmlu_machine_learning_generative', name: 'Machine Learning', count: 112, difficulty: 'Hard', category: 'STEM' },
				// Humanities
				{ id: 'mmlu_formal_logic_generative', name: 'Formal Logic', count: 126, difficulty: 'Hard', category: 'Humanities' },
				{ id: 'mmlu_high_school_european_history_generative', name: 'HS European History', count: 165, difficulty: 'Medium', category: 'Humanities' },
				{ id: 'mmlu_high_school_us_history_generative', name: 'HS US History', count: 204, difficulty: 'Medium', category: 'Humanities' },
				{ id: 'mmlu_high_school_world_history_generative', name: 'HS World History', count: 237, difficulty: 'Medium', category: 'Humanities' },
				{ id: 'mmlu_international_law_generative', name: 'International Law', count: 121, difficulty: 'Medium', category: 'Humanities' },
				{ id: 'mmlu_jurisprudence_generative', name: 'Jurisprudence', count: 108, difficulty: 'Medium-Hard', category: 'Humanities' },
				{ id: 'mmlu_logical_fallacies_generative', name: 'Logical Fallacies', count: 163, difficulty: 'Medium', category: 'Humanities' },
				{ id: 'mmlu_moral_disputes_generative', name: 'Moral Disputes', count: 346, difficulty: 'Medium-Hard', category: 'Humanities' },
				{ id: 'mmlu_moral_scenarios_generative', name: 'Moral Scenarios', count: 895, difficulty: 'Hard', category: 'Humanities' },
				{ id: 'mmlu_philosophy_generative', name: 'Philosophy', count: 311, difficulty: 'Medium-Hard', category: 'Humanities' },
				{ id: 'mmlu_prehistory_generative', name: 'Prehistory', count: 324, difficulty: 'Medium', category: 'Humanities' },
				{ id: 'mmlu_professional_law_generative', name: 'Professional Law', count: 1534, difficulty: 'Hard', category: 'Humanities' },
				{ id: 'mmlu_world_religions_generative', name: 'World Religions', count: 171, difficulty: 'Easy-Medium', category: 'Humanities' },
				// Social Sciences
				{ id: 'mmlu_econometrics_generative', name: 'Econometrics', count: 114, difficulty: 'Hard', category: 'Social Sciences' },
				{ id: 'mmlu_high_school_geography_generative', name: 'HS Geography', count: 198, difficulty: 'Medium', category: 'Social Sciences' },
				{ id: 'mmlu_high_school_government_and_politics_generative', name: 'HS Government & Politics', count: 193, difficulty: 'Medium', category: 'Social Sciences' },
				{ id: 'mmlu_high_school_macroeconomics_generative', name: 'HS Macroeconomics', count: 390, difficulty: 'Medium', category: 'Social Sciences' },
				{ id: 'mmlu_high_school_microeconomics_generative', name: 'HS Microeconomics', count: 238, difficulty: 'Medium', category: 'Social Sciences' },
				{ id: 'mmlu_high_school_psychology_generative', name: 'HS Psychology', count: 545, difficulty: 'Medium', category: 'Social Sciences' },
				{ id: 'mmlu_human_sexuality_generative', name: 'Human Sexuality', count: 131, difficulty: 'Medium', category: 'Social Sciences' },
				{ id: 'mmlu_professional_psychology_generative', name: 'Professional Psychology', count: 612, difficulty: 'Medium-Hard', category: 'Social Sciences' },
				{ id: 'mmlu_public_relations_generative', name: 'Public Relations', count: 110, difficulty: 'Medium', category: 'Social Sciences' },
				{ id: 'mmlu_security_studies_generative', name: 'Security Studies', count: 245, difficulty: 'Medium', category: 'Social Sciences' },
				{ id: 'mmlu_sociology_generative', name: 'Sociology', count: 201, difficulty: 'Medium', category: 'Social Sciences' },
				{ id: 'mmlu_us_foreign_policy_generative', name: 'US Foreign Policy', count: 100, difficulty: 'Medium', category: 'Social Sciences' },
				// Other
				{ id: 'mmlu_business_ethics_generative', name: 'Business Ethics', count: 100, difficulty: 'Medium', category: 'Other' },
				{ id: 'mmlu_clinical_knowledge_generative', name: 'Clinical Knowledge', count: 265, difficulty: 'Medium-Hard', category: 'Other' },
				{ id: 'mmlu_college_medicine_generative', name: 'College Medicine', count: 173, difficulty: 'Hard', category: 'Other' },
				{ id: 'mmlu_global_facts_generative', name: 'Global Facts', count: 100, difficulty: 'Hard', category: 'Other' },
				{ id: 'mmlu_human_aging_generative', name: 'Human Aging', count: 223, difficulty: 'Medium', category: 'Other' },
				{ id: 'mmlu_management_generative', name: 'Management', count: 103, difficulty: 'Medium', category: 'Other' },
				{ id: 'mmlu_marketing_generative', name: 'Marketing', count: 234, difficulty: 'Medium', category: 'Other' },
				{ id: 'mmlu_medical_genetics_generative', name: 'Medical Genetics', count: 100, difficulty: 'Medium-Hard', category: 'Other' },
				{ id: 'mmlu_miscellaneous_generative', name: 'Miscellaneous', count: 783, difficulty: 'Medium', category: 'Other' },
				{ id: 'mmlu_nutrition_generative', name: 'Nutrition', count: 306, difficulty: 'Medium', category: 'Other' },
				{ id: 'mmlu_professional_accounting_generative', name: 'Professional Accounting', count: 282, difficulty: 'Hard', category: 'Other' },
				{ id: 'mmlu_professional_medicine_generative', name: 'Professional Medicine', count: 272, difficulty: 'Hard', category: 'Other' },
				{ id: 'mmlu_virology_generative', name: 'Virology', count: 166, difficulty: 'Medium-Hard', category: 'Other' }
			]
		},
		{
			id: 'truthfulqa',
			name: 'TruthfulQA',
			description: 'Tests a model\'s tendency to reproduce common misconceptions and falsehoods. Multiple choice format with letter selection.',
			language: 'English',
			tasks: [
				{ id: 'truthfulqa_mc1_chat', name: 'TruthfulQA MC1', count: 817, difficulty: 'Medium' }
			]
		},
		{
			id: 'winogrande',
			name: 'Winogrande',
			description: 'Large-scale Winograd Schema challenge testing commonsense pronoun resolution.',
			language: 'English',
			tasks: [
				{ id: 'winogrande_chat', name: 'Winogrande', count: 1267, difficulty: 'Medium' }
			]
		},
		{
			id: 'gsm8k',
			name: 'GSM8K',
			description: 'Grade School Math 8K. Multi-step arithmetic word problems requiring careful reasoning.',
			language: 'English',
			tasks: [
				{ id: 'gsm8k', name: 'GSM8K', count: 1319, difficulty: 'Medium-Hard' }
			]
		}
	];

	// Bigcode benchmark families
	const benchmarkGroups = [
		{
			id: 'humaneval',
			name: 'HumanEval',
			description: 'Hand-written Python programming problems with unit tests. Tests language comprehension, algorithms, and simple math.',
			language: 'Python',
			tasks: [
				{ id: 'humaneval', name: 'HumanEval', count: 164, difficulty: 'Medium' },
				{ id: 'humanevalplus', name: 'HumanEval+', count: 164, difficulty: 'Medium' }
			]
		},
		{
			id: 'mbpp',
			name: 'MBPP',
			description: 'Mostly Basic Python Programming. Crowd-sourced Python programming problems covering basic concepts.',
			language: 'Python',
			tasks: [
				{ id: 'mbpp', name: 'MBPP', count: 974, difficulty: 'Easy-Medium' },
				{ id: 'mbppplus', name: 'MBPP+', count: 974, difficulty: 'Easy-Medium' }
			]
		},
		{
			id: 'apps',
			name: 'APPS',
			description: 'Python programming problems across three difficulty tiers: introductory, interview, and competition.',
			language: 'Python',
			tasks: [
				{ id: 'apps-introductory', name: 'Introductory', count: 3639, difficulty: 'Easy' },
				{ id: 'apps-interview', name: 'Interview', count: 5000, difficulty: 'Medium' },
				{ id: 'apps-competition', name: 'Competition', count: 1361, difficulty: 'Hard' }
			]
		},
		{
			id: 'ds1000',
			name: 'DS-1000',
			description: 'Data science coding problems across NumPy, Pandas, SciPy, Matplotlib, Sklearn, TensorFlow, and PyTorch.',
			language: 'Python',
			tasks: [
				{ id: 'ds1000-numpy-completion', name: 'NumPy', count: 220, difficulty: 'Medium' },
				{ id: 'ds1000-pandas-completion', name: 'Pandas', count: 291, difficulty: 'Medium' },
				{ id: 'ds1000-scipy-completion', name: 'SciPy', count: 106, difficulty: 'Medium-Hard' },
				{ id: 'ds1000-matplotlib-completion', name: 'Matplotlib', count: 155, difficulty: 'Medium' },
				{ id: 'ds1000-sklearn-completion', name: 'Sklearn', count: 115, difficulty: 'Medium-Hard' },
				{ id: 'ds1000-tensorflow-completion', name: 'TensorFlow', count: 45, difficulty: 'Hard' },
				{ id: 'ds1000-pytorch-completion', name: 'PyTorch', count: 68, difficulty: 'Hard' }
			]
		},
		{
			id: 'multiple',
			name: 'MultiPL-E',
			description: 'HumanEval programming problems translated into 20+ languages via the MultiPL-E framework.',
			language: 'Multi-language',
			tasks: [
				{ id: 'multiple-py', name: 'Python', count: 164, difficulty: 'Medium' },
				{ id: 'multiple-js', name: 'JavaScript', count: 164, difficulty: 'Medium' },
				{ id: 'multiple-ts', name: 'TypeScript', count: 164, difficulty: 'Medium' },
				{ id: 'multiple-java', name: 'Java', count: 164, difficulty: 'Medium' },
				{ id: 'multiple-cpp', name: 'C++', count: 164, difficulty: 'Medium' },
				{ id: 'multiple-cs', name: 'C#', count: 164, difficulty: 'Medium' },
				{ id: 'multiple-go', name: 'Go', count: 164, difficulty: 'Medium' },
				{ id: 'multiple-rs', name: 'Rust', count: 164, difficulty: 'Medium' },
				{ id: 'multiple-rb', name: 'Ruby', count: 164, difficulty: 'Medium' },
				{ id: 'multiple-php', name: 'PHP', count: 164, difficulty: 'Medium' },
				{ id: 'multiple-sh', name: 'Bash', count: 164, difficulty: 'Medium' },
				{ id: 'multiple-scala', name: 'Scala', count: 164, difficulty: 'Medium' },
				{ id: 'multiple-lua', name: 'Lua', count: 164, difficulty: 'Medium' },
				{ id: 'multiple-r', name: 'R', count: 164, difficulty: 'Medium' },
				{ id: 'multiple-pl', name: 'Perl', count: 164, difficulty: 'Medium' },
				{ id: 'multiple-rkt', name: 'Racket', count: 164, difficulty: 'Medium' }
			]
		}
	];

	const difficultyColor = (d: string) => {
		if (d.startsWith('Easy')) return 'text-green-600 dark:text-green-400';
		if (d === 'Medium') return 'text-yellow-600 dark:text-yellow-400';
		return 'text-orange-600 dark:text-orange-400';
	};

	const statusColor = (s: string) => {
		switch (s) {
			case 'completed': return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400';
			case 'running': return 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400';
			case 'queued': return 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400';
			case 'pending': return 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400';
			case 'failed': return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400';
			case 'cancelled': return 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-500';
			default: return 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400';
		}
	};

	const loadModels = async () => {
		try {
			const allModels = await getModels(getToken());
			modelItems = (allModels ?? []).map((m: any) => ({
				value: m.id,
				label: m.name ?? m.id
			}));
		} catch (e) {
			console.error('Failed to load models:', e);
		}
	};

	const openGroupModal = async (group: BenchmarkGroup, evalType: 'bigcode' | 'lm-eval' = 'bigcode') => {
		activeGroup = group;
		activeEvalType = evalType;
		selectedTasks = new Set(group.tasks.map((t) => t.id));
		jobModelId = '';
		showJobModal = true;
		if (modelItems.length === 0) {
			await loadModels();
		}
	};

	const toggleTask = (taskId: string) => {
		const next = new Set(selectedTasks);
		if (next.has(taskId)) {
			next.delete(taskId);
		} else {
			next.add(taskId);
		}
		selectedTasks = next;
	};

	const handleSubmitJob = async () => {
		if (!jobDryRun && !jobModelId) {
			toast.error($i18n.t('Please select a model.'));
			return;
		}
		if (selectedTasks.size === 0) {
			toast.error($i18n.t('Please select at least one test.'));
			return;
		}
		submitting = true;
		let taskList: string;
		if (activeEvalType === 'lm-eval') {
			// Map of group IDs to their lm-eval group task name (used when all subtasks selected)
			const groupShortcuts: Record<string, string> = {
				bbh_cot_zeroshot: 'bbh_cot_zeroshot',
				bbh_cot_fewshot: 'bbh_cot_fewshot',
				math_hard: 'leaderboard_math_hard',
				gpqa: 'leaderboard_gpqa',
				musr: 'leaderboard_musr_chat',
				mmlu_pro: 'mmlu_pro',
				mmlu: 'mmlu_generative',
				hellaswag: 'hellaswag_chat_split'
			};
			const shortcut = activeGroup && groupShortcuts[activeGroup.id];
			if (shortcut && selectedTasks.size === activeGroup!.tasks.length) {
				taskList = shortcut;
			} else {
				taskList = [...selectedTasks].join(',');
			}
		} else {
			// DS-1000: when all subtests are selected, use the "all" variant instead of individual ones
			if (activeGroup && activeGroup.id === 'ds1000' && selectedTasks.size === activeGroup.tasks.length) {
				taskList = 'ds1000-all-completion';
			} else {
				taskList = [...selectedTasks].join(',');
			}
		}
		// Sum sample counts for selected tasks
		const totalSamples = activeGroup!.tasks
			.filter((t) => selectedTasks.has(t.id))
			.reduce((sum, t) => sum + (t.count || 0), 0);

		try {
			const effectiveModelId = jobDryRun ? 'dry_run' : jobModelId;
			await createEvalJob(getToken(), taskList, effectiveModelId, activeEvalType, totalSamples, jobDryRun);
			toast.success($i18n.t('Evaluation job submitted and pending admin approval.'));
			showJobModal = false;
			jobs = await getEvalJobs(getToken());
		} catch (e) {
			toast.error(typeof e === 'string' ? e : $i18n.t('Failed to submit evaluation job.'));
		} finally {
			submitting = false;
		}
	};

	const handleCancel = async (id: string) => {
		try {
			await cancelEvalJob(getToken(), id);
			jobs = await getEvalJobs(getToken());
			toast.success($i18n.t('Evaluation job cancelled.'));
		} catch (e) {
			toast.error(typeof e === 'string' ? e : $i18n.t('Failed to cancel job.'));
		}
	};

	// Resolve a benchmark string (possibly comma-separated) to a human-readable name
	const getJobDisplayName = (benchmark: string) => {
		// Known group task shortcuts
		const groupNames: Record<string, string> = {
			'ds1000-all-completion': 'DS-1000',
			'bbh_cot_zeroshot': 'BBH (CoT Zero-shot)',
			'bbh_cot_fewshot': 'BBH (CoT Few-shot)',
			'leaderboard_math_hard': 'MATH Hard',
			'leaderboard_gpqa': 'GPQA',
			'leaderboard_musr': 'MUSR',
			'leaderboard_musr_chat': 'MUSR',
			'mmlu_pro': 'MMLU-PRO',
			'mmlu': 'MMLU',
			'mmlu_generative': 'MMLU',
			'hellaswag_split': 'HellaSwag',
			'hellaswag_chat_split': 'HellaSwag',
			'leaderboard': 'Open LLM Leaderboard v2'
		};
		if (groupNames[benchmark]) return groupNames[benchmark];
		const taskIds = benchmark.split(',').map((s) => s.trim());
		const allGroups = [...benchmarkGroups, ...leaderboardGroups];
		for (const group of allGroups) {
			const groupIds = group.tasks.map((t) => t.id);
			const allMatch = taskIds.every((id) => groupIds.includes(id));
			if (allMatch) {
				if (taskIds.length === groupIds.length) return group.name;
				const names = taskIds.map((id) => group.tasks.find((t) => t.id === id)?.name ?? id);
				return `${group.name}: ${names.join(', ')}`;
			}
		}
		return benchmark;
	};

	onMount(async () => {
		try {
			jobs = await getEvalJobs(getToken());
		} catch (e) {
			console.error('Failed to load eval jobs:', e);
		} finally {
			loaded = true;
		}
	});
</script>

<svelte:head>
	<title>{$i18n.t('Evaluations')} | {$WEBUI_NAME}</title>
</svelte:head>

{#if !loaded}
	<div class="w-full h-full flex justify-center items-center">
		<Spinner />
	</div>
{:else}
	<div class="flex flex-col gap-1 my-1.5">
		<div class="flex justify-between items-center">
			<div class="flex md:self-center text-xl font-medium px-0.5 items-center">
				{$i18n.t('Language & Understanding Evals')}
			</div>
		</div>
		<div class="text-xs text-gray-500 dark:text-gray-400 px-0.5">
			{$i18n.t('Language and understanding benchmarks. Select a benchmark to evaluate a model.')}
		</div>
	</div>

	<!-- Language & Understanding Benchmark Cards -->
	<div class="mt-3 mb-5 grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-3">
		{#each leaderboardGroups as group}
			<button
				class="flex flex-col text-left w-full px-4 py-3 rounded-xl border transition group {group.gated
					? 'border-gray-200 dark:border-gray-800 opacity-60 cursor-not-allowed'
					: 'border-gray-200 dark:border-gray-800 hover:border-purple-300 dark:hover:border-purple-700 hover:bg-purple-50/50 dark:hover:bg-purple-950/20'}"
				on:click={() => { if (!group.gated) openGroupModal(group, 'lm-eval'); else toast.error($i18n.t('This dataset requires HuggingFace authentication. Configure HF_TOKEN in the lm-eval container.')); }}
			>
				<div class="flex items-center justify-between w-full mb-1.5">
					<div class="font-semibold text-sm">{group.name}</div>
					{#if group.gated}
						<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-4 text-yellow-500">
							<path fill-rule="evenodd" d="M10 1a4.5 4.5 0 00-4.5 4.5V9H5a2 2 0 00-2 2v6a2 2 0 002 2h10a2 2 0 002-2v-6a2 2 0 00-2-2h-.5V5.5A4.5 4.5 0 0010 1zm3 8V5.5a3 3 0 10-6 0V9h6z" clip-rule="evenodd" />
						</svg>
					{:else}
						<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-4 text-gray-400 group-hover:text-purple-500 transition">
							<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z" clip-rule="evenodd" />
						</svg>
					{/if}
				</div>
				<div class="text-xs text-gray-500 dark:text-gray-400 mb-2 line-clamp-2">
					{group.description}
				</div>
				<div class="flex flex-wrap gap-1.5 mt-auto">
					<span class="px-1.5 py-0.5 rounded text-[10px] font-medium bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300">
						{group.language}
					</span>
					<span class="px-1.5 py-0.5 rounded text-[10px] font-medium bg-purple-50 text-purple-700 dark:bg-purple-900/20 dark:text-purple-300">
						{#if group.tasks.length === 1}
							{group.tasks[0].count.toLocaleString()} questions
						{:else}
							{group.tasks.length} subtests
						{/if}
					</span>
					{#if group.gated}
						<span class="px-1.5 py-0.5 rounded text-[10px] font-medium bg-yellow-50 text-yellow-700 dark:bg-yellow-900/20 dark:text-yellow-400">
							HF Auth Required
						</span>
					{/if}
				</div>
			</button>
		{/each}
	</div>

	<div class="flex flex-col gap-1 my-1.5">
		<div class="flex justify-between items-center">
			<div class="flex md:self-center text-xl font-medium px-0.5 items-center">
				{$i18n.t('Code Evaluations')}
			</div>
		</div>
		<div class="text-xs text-gray-500 dark:text-gray-400 px-0.5">
			{$i18n.t('Select a benchmark family to evaluate a model. You can deselect individual subtests before submitting.')}
		</div>
	</div>

	<!-- Benchmark Family Cards -->
	<div class="mt-3 mb-5 grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-3">
		{#each benchmarkGroups as group}
			<button
				class="flex flex-col text-left w-full px-4 py-3 rounded-xl border border-gray-200 dark:border-gray-800 hover:border-blue-300 dark:hover:border-blue-700 hover:bg-blue-50/50 dark:hover:bg-blue-950/20 transition group"
				on:click={() => openGroupModal(group)}
			>
				<div class="flex items-center justify-between w-full mb-1.5">
					<div class="font-semibold text-sm">{group.name}</div>
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-4 text-gray-400 group-hover:text-blue-500 transition">
						<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z" clip-rule="evenodd" />
					</svg>
				</div>
				<div class="text-xs text-gray-500 dark:text-gray-400 mb-2 line-clamp-2">
					{group.description}
				</div>
				<div class="flex flex-wrap gap-1.5 mt-auto">
					<span class="px-1.5 py-0.5 rounded text-[10px] font-medium bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300">
						{group.language}
					</span>
					<span class="px-1.5 py-0.5 rounded text-[10px] font-medium bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-300">
						{group.tasks.length} subtests
					</span>
				</div>
			</button>
		{/each}
	</div>

	<!-- Submitted Jobs -->
	{#if jobs.length > 0}
		<div class="mb-4">
			<div class="flex items-center text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 px-0.5">
				{$i18n.t('Your Evaluation Jobs')}
				<div class="flex self-center w-[1px] h-5 mx-2 bg-gray-200 dark:bg-gray-700" />
				<span class="text-gray-500 dark:text-gray-400 font-normal">{jobs.length}</span>
			</div>
			<div class="space-y-1.5">
				{#each jobs as job}
					<div class="flex items-center justify-between px-3 py-2 rounded-xl border border-gray-100 dark:border-gray-800 text-sm">
						<div class="flex items-center gap-3">
							<span class="px-2 py-0.5 rounded-lg text-[11px] font-medium {statusColor(job.status)}">
								{job.status}
							</span>
							<span class="px-1.5 py-0.5 rounded text-[10px] font-medium {job.eval_type === 'lm-eval' ? 'bg-purple-50 text-purple-700 dark:bg-purple-900/20 dark:text-purple-300' : 'bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-300'}">
								{job.eval_type === 'lm-eval' ? 'LLM' : 'Code'}
							</span>
							<div>
								<span class="font-medium">{getJobDisplayName(job.benchmark)}</span>
								<span class="text-gray-400 mx-1.5">&mdash;</span>
								<span class="text-gray-500 dark:text-gray-400 text-xs font-mono">{job.model_id}</span>
							</div>
						</div>
						<div class="flex items-center gap-2">
							<span class="text-xs text-gray-400">{dayjs(job.created_at * 1000).fromNow()}</span>
							{#if ['pending', 'queued', 'running'].includes(job.status)}
								<Tooltip content={$i18n.t('Cancel')}>
									<button
										class="p-1 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-800 transition"
										on:click={() => handleCancel(job.id)}
									>
										<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-3.5 text-gray-500 hover:text-red-500 transition">
											<path fill-rule="evenodd" d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" clip-rule="evenodd" />
										</svg>
									</button>
								</Tooltip>
							{/if}
							{#if job.error_message}
								<Tooltip content={job.error_message}>
									<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-3.5 text-red-500">
										<path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-5a.75.75 0 01.75.75v4.5a.75.75 0 01-1.5 0v-4.5A.75.75 0 0110 5zm0 10a1 1 0 100-2 1 1 0 000 2z" clip-rule="evenodd" />
									</svg>
								</Tooltip>
							{/if}
						</div>
					</div>
				{/each}
			</div>
		</div>
	{/if}
{/if}

<!-- Submit Job Modal -->
{#if showJobModal && activeGroup}
	<!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
	<div class="fixed inset-0 z-50 flex items-center justify-center bg-black/40" on:click|self={() => (showJobModal = false)}>
		<div class="bg-white dark:bg-gray-900 rounded-2xl shadow-xl p-6 w-full mx-4 max-h-[90vh] flex flex-col {activeGroup.tasks.length > 20 ? 'max-w-2xl' : 'max-w-md'}">
			<div class="font-semibold text-base mb-0.5">{$i18n.t('Submit Evaluation Job')}</div>
			<div class="text-sm text-gray-500 dark:text-gray-400 mb-4">{activeGroup.name}</div>

			<!-- Model selector -->
			<div class="mb-4 relative">
				<div class="text-xs text-gray-500 dark:text-gray-400 mb-1">{$i18n.t('Model')}</div>
				{#if jobDryRun}
					<div
						class="w-full rounded-xl px-3 py-2 text-sm text-left bg-gray-100 dark:bg-gray-850 text-gray-400 dark:text-gray-500 border border-gray-200 dark:border-gray-700 cursor-not-allowed italic"
					>
						dry_run
					</div>
				{:else}
					<button
						type="button"
						class="w-full rounded-xl px-3 py-2 text-sm text-left bg-gray-50 dark:bg-gray-800 dark:text-gray-100 border border-gray-200 dark:border-gray-700 flex items-center justify-between"
						on:click={() => { showModelDropdown = !showModelDropdown; modelSearch = ''; }}
					>
						<span class={jobModelId ? '' : 'text-gray-400'}>
							{jobModelId ? (modelItems.find((m) => m.value === jobModelId)?.label ?? jobModelId) : $i18n.t('Select a model')}
						</span>
						<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-4 text-gray-400">
							<path fill-rule="evenodd" d="M5.22 8.22a.75.75 0 011.06 0L10 11.94l3.72-3.72a.75.75 0 111.06 1.06l-4.25 4.25a.75.75 0 01-1.06 0L5.22 9.28a.75.75 0 010-1.06z" clip-rule="evenodd" />
						</svg>
					</button>

					{#if showModelDropdown}
						<div class="absolute z-[60] mt-1 w-full rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 shadow-lg">
							<div class="p-2">
								<input
									class="w-full rounded-lg px-3 py-1.5 text-sm bg-gray-50 dark:bg-gray-900 dark:text-gray-100 outline-none border border-gray-200 dark:border-gray-700"
									bind:value={modelSearch}
									placeholder={$i18n.t('Search models...')}
								/>
							</div>
							<div class="max-h-48 overflow-y-auto px-1 pb-1">
								{#each filteredModels as model}
									<button
										type="button"
										class="w-full text-left px-3 py-1.5 text-sm rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition {jobModelId === model.value ? 'bg-gray-100 dark:bg-gray-700 font-medium' : ''}"
										on:click={() => { jobModelId = model.value; showModelDropdown = false; }}
									>
										{model.label}
									</button>
								{:else}
									<div class="px-3 py-2 text-sm text-gray-400">{$i18n.t('No models found')}</div>
								{/each}
							</div>
						</div>
					{/if}
				{/if}
			</div>

			<!-- Task checklist (multi-task) or info (single-task) -->
			{#if activeGroup.tasks.length === 1}
				<div class="mb-4 px-3 py-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
					<div class="flex items-center justify-between">
						<span class="text-sm font-medium">{activeGroup.tasks[0].name}</span>
						<span class="text-xs {difficultyColor(activeGroup.tasks[0].difficulty)}">{activeGroup.tasks[0].difficulty}</span>
					</div>
					<div class="text-xs text-gray-500 dark:text-gray-400 mt-1">
						{activeGroup.tasks[0].count.toLocaleString()} questions
					</div>
				</div>
			{:else}
				{@const hasCategories = activeGroup.tasks.some((t) => t.category)}
				{@const categories = hasCategories ? [...new Set(activeGroup.tasks.map((t) => t.category))] : [null]}
				<div class="mb-4 flex-1 overflow-hidden flex flex-col min-h-0">
					<div class="flex items-center justify-between mb-1.5">
						<div class="text-xs text-gray-500 dark:text-gray-400">{$i18n.t('Tests')}</div>
						<div class="flex gap-2">
							<button
								type="button"
								class="text-[11px] text-blue-600 dark:text-blue-400 hover:underline"
								on:click={() => { if (activeGroup) selectedTasks = new Set(activeGroup.tasks.map((t) => t.id)); }}
							>{$i18n.t('Select all')}</button>
							<span class="text-gray-300 dark:text-gray-600">|</span>
							<button
								type="button"
								class="text-[11px] text-gray-500 dark:text-gray-400 hover:underline"
								on:click={() => { selectedTasks = new Set(); }}
							>{$i18n.t('Deselect all')}</button>
						</div>
					</div>
					<div class="overflow-y-auto border border-gray-200 dark:border-gray-700 rounded-xl divide-y divide-gray-100 dark:divide-gray-800">
						{#each categories as cat}
							{@const catTasks = cat ? activeGroup.tasks.filter((t) => t.category === cat) : activeGroup.tasks}
							{#if cat}
								<div class="flex items-center justify-between px-3 py-1.5 bg-gray-50 dark:bg-gray-800/80 sticky top-0 z-10">
									<span class="text-[11px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">{cat}</span>
									<div class="flex gap-2">
										<button
											type="button"
											class="text-[10px] text-blue-600 dark:text-blue-400 hover:underline"
											on:click={() => {
												const next = new Set(selectedTasks);
												catTasks.forEach((t) => next.add(t.id));
												selectedTasks = next;
											}}
										>{$i18n.t('All')}</button>
										<button
											type="button"
											class="text-[10px] text-gray-500 dark:text-gray-400 hover:underline"
											on:click={() => {
												const next = new Set(selectedTasks);
												catTasks.forEach((t) => next.delete(t.id));
												selectedTasks = next;
											}}
										>{$i18n.t('None')}</button>
									</div>
								</div>
							{/if}
							{#each catTasks as task}
								<!-- svelte-ignore a11y-click-events-have-key-events -->
								<label class="flex items-center gap-3 px-3 py-2 hover:bg-gray-50 dark:hover:bg-gray-800/50 cursor-pointer transition">
									<input
										type="checkbox"
										class="rounded accent-blue-600"
										checked={selectedTasks.has(task.id)}
										on:change={() => toggleTask(task.id)}
									/>
									<span class="text-sm flex-1">{task.name}</span>
									<span class="text-[10px] {difficultyColor(task.difficulty)}">{task.difficulty}</span>
									<span class="text-[10px] text-gray-400 tabular-nums">{task.count.toLocaleString()}</span>
								</label>
							{/each}
						{/each}
					</div>
					<div class="mt-1.5 text-[11px] text-gray-400 dark:text-gray-500">
						{selectedTasks.size} of {activeGroup.tasks.length} tests selected
					</div>
				</div>
			{/if}

			<div class="flex items-center gap-2 mb-3">
				<label class="flex items-center gap-2 cursor-pointer select-none">
					<input
						type="checkbox"
						bind:checked={jobDryRun}
						on:change={() => { if (jobDryRun) showModelDropdown = false; }}
						class="rounded border-gray-300 dark:border-gray-700 text-orange-500 focus:ring-orange-500 dark:bg-gray-900"
					/>
					<span class="text-xs font-medium {jobDryRun ? 'text-orange-600 dark:text-orange-400' : 'text-gray-500 dark:text-gray-400'}">
						{$i18n.t('Test Mode')}
					</span>
				</label>
				{#if jobDryRun}
					<span class="text-[10px] text-orange-500 dark:text-orange-400">
						Synthetic data — no model inference
					</span>
				{/if}
			</div>

			<div class="text-xs text-gray-400 dark:text-gray-500 mb-4">
				{$i18n.t('The job will be submitted for admin approval before the evaluation begins.')}
			</div>

			<div class="flex justify-end gap-2">
				<button class="px-3 py-1.5 rounded-xl text-sm hover:bg-gray-100 dark:hover:bg-gray-800 transition" on:click={() => (showJobModal = false)}>
					{$i18n.t('Cancel')}
				</button>
				<button
					class="px-4 py-1.5 rounded-xl text-sm font-medium {jobDryRun ? 'bg-orange-500 hover:bg-orange-600' : 'bg-blue-600 hover:bg-blue-700'} text-white transition disabled:opacity-50"
					on:click={handleSubmitJob}
					disabled={submitting || (!jobDryRun && !jobModelId) || selectedTasks.size === 0}
				>
					{submitting ? $i18n.t('Submitting...') : jobDryRun ? $i18n.t('Submit Test') : $i18n.t('Submit Job')}
				</button>
			</div>
		</div>
	</div>
{/if}
