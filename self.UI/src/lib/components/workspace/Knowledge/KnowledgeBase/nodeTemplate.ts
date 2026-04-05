export type ParamDef = {
    name: string;
    label: string;
    type: 'string' | 'number' | 'boolean' | 'string_list' | 'select';
    required: boolean;
    default?: string | number | boolean | string[] | null;
    options?: string[];
};

export type NodeTemplate = {
    stageType: string;
    label: string;
    category: string;
    headerColor: string;
    description: string;
    params: ParamDef[];
};

export const DOCUMENT_SPLITTER_TEMPLATE: NodeTemplate = {
    stageType: 'DocumentSplitter',
    label: 'DocumentSplitter',
    category: 'document_ops',
    headerColor: 'bg-rose-950',
    description: 'Splits documents into segments based on a defined separator',
    params: [
        { name: 'separator', label: 'Seperator', type: 'string', required: true},
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
        { name: 'segment_id_field', label: 'Segment ID Field', type: 'string', required: false, default: 'segment_id'},
    ]
};

export const DOCUMENT_JOINER_TEMPLATE: NodeTemplate = {
    stageType: 'DocumentJoiner',
    label: 'DocumentJoiner',
    category: 'document_ops',
    headerColor: 'bg-violet-600',
    description: 'Joins documents together',
    params: [
        { name: 'separator', label: 'Seperator', type: 'string', required: false, default: '\n\n'},
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
        { name: 'segment_id_field', label: 'Segment ID Field', type: 'string', required: false, default: 'segment_id'},
        { name: 'drop_segment_id_field', label: 'Drop Segment ID', type: 'boolean', required: false, default: true},
        { name: 'document_id_field', label: 'Document ID Field', type: 'string', required: false, default: 'id'},
        //TODO: These need to be codependent. And I need to understand the 'length_field' value better. I think I will populate that with the api
        { name: 'max_length', label: 'Max Characters', type: 'number', required: false, default: null },
        { name: 'length_field', label: 'Length Field', type: 'string', required: false, default: null},
    ],
};

export const WORD_COUNT_FILTER_TEMPLATE: NodeTemplate = {
    stageType: 'WordCountFilter',
    label: 'Word Count Filter',
    category: 'filters',
    headerColor: 'bg-amber-600',
    description: 'Keep documents within a word count range',
    params: [
        { name: 'min_words', label: 'Min Words', type: 'number', required: false, default: 50 },
        { name: 'max_words', label: 'Max Words', type: 'number', required: false, default: 100000 },
        { name: 'lang', label: 'Language', type: 'string', required: false, default: 'en' },
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
        { name: 'score_field', label: 'Score Field', type: 'string', required: false, default: null },
        { name: 'invert', label: 'Invert', type: 'boolean', required: false, default: false },
    ],
};

export const NON_ALPHA_NUMERIC_FILTER_TEMPLATE: NodeTemplate = {
    stageType: 'NonAlphaNumericFilter',
    label: 'Non-AlphaNumeric Filter',
    category: 'filters',
    headerColor: 'bg-amber-600',
    description: 'Discard documents with too many non-alphanumeric characters',
    params: [
        { name: 'max_non_alpha_numeric_to_text_ratio', label: 'Max Non-AlphaNumeric Ratio', type: 'number', required: false, default: 0.25 },
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
        { name: 'score_field', label: 'Score Field', type: 'string', required: false, default: null },
        { name: 'invert', label: 'Invert', type: 'boolean', required: false, default: false },
    ],
};

export const URLS_FILTER_TEMPLATE: NodeTemplate = {
    stageType: 'UrlsFilter',
    label: 'URL Filter',
    category: 'filters',
    headerColor: 'bg-amber-600',
    description: 'Discard documents with too many URLs',
    params: [
        { name: 'max_url_to_text_ratio', label: 'Max URL to Text Ratio', type: 'number', required: false, default: 0.2 },
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
        { name: 'score_field', label: 'Score Field', type: 'string', required: false, default: null },
        { name: 'invert', label: 'Invert', type: 'boolean', required: false, default: false },
    ],
};

export const NUMBERS_FILTER_TEMPLATE: NodeTemplate = {
    stageType: 'NumbersFilter',
    label: 'Numbers Filter',
    category: 'filters',
    headerColor: 'bg-amber-600',
    description: 'Discard documents with too many numeric characters',
    params: [
        { name: 'max_number_to_text_ratio', label: 'Max Number to Text Ratio', type: 'number', required: false, default: 0.15 },
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
        { name: 'score_field', label: 'Score Field', type: 'string', required: false, default: null },
        { name: 'invert', label: 'Invert', type: 'boolean', required: false, default: false },
    ],
};

export const WHITESPACE_FILTER_TEMPLATE: NodeTemplate = {
    stageType: 'WhiteSpaceFilter',
    label: 'Whitespace Filter',
    category: 'filters',
    headerColor: 'bg-amber-600',
    description: 'Discard documents with excessive whitespace',
    params: [
        { name: 'max_white_space_ratio', label: 'Max Whitespace Ratio', type: 'number', required: false, default: 0.25 },
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
        { name: 'score_field', label: 'Score Field', type: 'string', required: false, default: null },
        { name: 'invert', label: 'Invert', type: 'boolean', required: false, default: false },
    ],
};

export const BULLETS_FILTER_TEMPLATE: NodeTemplate = {
    stageType: 'BulletsFilter',
    label: 'Bullets Filter',
    category: 'filters',
    headerColor: 'bg-amber-600',
    description: 'Discard documents where most lines start with a bullet',
    params: [
        { name: 'max_bullet_lines_ratio', label: 'Max Bullet Lines Ratio', type: 'number', required: false, default: 0.9 },
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
        { name: 'score_field', label: 'Score Field', type: 'string', required: false, default: null },
        { name: 'invert', label: 'Invert', type: 'boolean', required: false, default: false },
    ],
};

export const LONG_WORD_FILTER_TEMPLATE: NodeTemplate = {
    stageType: 'LongWordFilter',
    label: 'Long Word Filter',
    category: 'filters',
    headerColor: 'bg-amber-600',
    description: 'Discard documents containing words over a length threshold',
    params: [
        { name: 'max_word_length', label: 'Max Word Length', type: 'number', required: false, default: 1000 },
        { name: 'lang', label: 'Language', type: 'string', required: false, default: 'en' },
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
        { name: 'score_field', label: 'Score Field', type: 'string', required: false, default: null },
        { name: 'invert', label: 'Invert', type: 'boolean', required: false, default: false },
    ],
};

export const BOILERPLATE_STRING_FILTER_TEMPLATE: NodeTemplate = {
    stageType: 'BoilerPlateStringFilter',
    label: 'Boilerplate Filter',
    category: 'filters',
    headerColor: 'bg-amber-600',
    description: 'Discard documents with too many boilerplate strings',
    params: [
        { name: 'remove_if_at_top_or_bottom', label: 'Remove if at Top/Bottom', type: 'boolean', required: false, default: true },
        { name: 'max_boilerplate_string_ratio', label: 'Max Boilerplate Ratio', type: 'number', required: false, default: 0.4 },
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
        { name: 'score_field', label: 'Score Field', type: 'string', required: false, default: null },
        { name: 'invert', label: 'Invert', type: 'boolean', required: false, default: false },
    ],
};

export const BOILERPLATE_STRING_MODIFIER_TEMPLATE: NodeTemplate = {
    stageType: 'BoilerPlateStringModifier',
    label: 'Boilerplate String modifier',
    category: 'modifiers',
    headerColor: 'bg-teal-600',
    description: 'Apply C4 Preprocessing rules',
    params: [
        { name: 'remove_if_at_top_or_bottom', label: 'Remove if at Top/Bottom', type: 'boolean', required: false, default: true },
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
    ],
};

export const QUOTATION_REMOVER_MODIFIER_TEMPLATE: NodeTemplate = {
    stageType: 'QuotationRemover',
    label: 'Remove Quotation Marks',
    category: 'modifiers',
    headerColor: 'bg-teal-600',
    description: 'Remove Surronding Quotation Marks from documents',
    params: [
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
    ],
};

export const MARKDOWN_REMOVER_MODIFIER_TEMPLATE: NodeTemplate = {
    stageType: 'MarkdownRemover',
    label: 'Strip Markdown',
    category: 'modifiers',
    headerColor: 'bg-teal-600',
    description: 'Remove Markdown formatting from a document',
    params: [
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
    ],
};

export const NEWLINE_NORMALIZER_MODIFIER_TEMPLATE: NodeTemplate = {
    stageType: 'NewlineNormalizer',
    label: 'Newline Normalizer',
    category: 'modifiers',
    headerColor: 'bg-teal-600',
    description: 'Standarize how new lines are defined in a document',
    params: [
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
    ],
};

export const SLICER_MODIFIER_TEMPLATE: NodeTemplate = {
    stageType: 'Slicer',
    label: 'Slicer',
    category: 'modifiers',
    headerColor: 'bg-teal-600',
    description: 'Slice strings at specific locations',
    params: [
        { name: 'left', label: 'Left', type: 'number', required: false, default: 0 },
        { name: 'right', label: 'Right', type: 'number', required: false, default: null },
        { name: 'include_left', label: 'Include Left', type: 'boolean', required: false, default: true },
        { name: 'include_right', label: 'Include Right', type: 'boolean', required: false, default: true },
        { name: 'strip', label: 'Strip', type: 'boolean', required: false, default: true },
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
    ],
};

export const URL_REMOVER_MODIFIER_TEMPLATE: NodeTemplate = {
    stageType: 'UrlRemover',
    label: 'Remove Urls',
    category: 'modifiers',
    headerColor: 'bg-teal-600',
    description: 'Remove urls from documents',
    params: [
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
    ],
};

export const LINE_REMOVER_MODIFIER_TEMPLATE: NodeTemplate = {
    stageType: 'LineRemover',
    label: 'Line Remover',
    category: 'modifiers',
    headerColor: 'bg-teal-600',
    description: 'Remove lines matching specific patterns',
    params: [
        { name: 'patterns', label: 'Patterns (one per line)', type: 'string_list', required: true },
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
    ],
};

export const UNICODE_REFORMATTER_MODIFIER_TEMPLATE: NodeTemplate = {
    stageType: 'UnicodeReformatter',
    label: 'Unicode Reformatter',
    category: 'modifiers',
    headerColor: 'bg-teal-600',
    description: 'Fix Unicode encoding issues using ftfy',
    params: [
        { name: 'unescape_html', label: 'Unescape HTML', type: 'string', required: false, default: 'auto' },
        { name: 'remove_terminal_escapes', label: 'Remove Terminal Escapes', type: 'boolean', required: false, default: true },
        { name: 'fix_encoding', label: 'Fix Encoding', type: 'boolean', required: false, default: true },
        { name: 'restore_byte_a0', label: 'Restore Byte A0', type: 'boolean', required: false, default: true },
        { name: 'replace_lossy_sequences', label: 'Replace Lossy Sequences', type: 'boolean', required: false, default: true },
        { name: 'decode_inconsistent_utf8', label: 'Decode Inconsistent UTF-8', type: 'boolean', required: false, default: true },
        { name: 'fix_c1_controls', label: 'Fix C1 Controls', type: 'boolean', required: false, default: true },
        { name: 'fix_latin_ligatures', label: 'Fix Latin Ligatures', type: 'boolean', required: false, default: false },
        { name: 'fix_character_width', label: 'Fix Character Width', type: 'boolean', required: false, default: false },
        { name: 'uncurl_quotes', label: 'Uncurl Quotes', type: 'boolean', required: false, default: false },
        { name: 'fix_line_breaks', label: 'Fix Line Breaks', type: 'boolean', required: false, default: false },
        { name: 'fix_surrogates', label: 'Fix Surrogates', type: 'boolean', required: false, default: true },
        { name: 'remove_control_chars', label: 'Remove Control Chars', type: 'boolean', required: false, default: true },
        { name: 'normalization', label: 'Normalization', type: 'string', required: false, default: null },
        { name: 'max_decode_length', label: 'Max Decode Length', type: 'number', required: false, default: 1000000 },
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
    ],
};

export const QUALITY_CLASSIFIER_TEMPLATE: NodeTemplate = {
    stageType: 'QualityClassifier',
    label: 'Quality Classifier',
    category: 'classifiers',
    headerColor: 'bg-purple-600',
    description: 'Score and optionally filter documents by quality using a DeBERTa model',
    params: [
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
        { name: 'label_field', label: 'Label Field', type: 'string', required: false, default: 'quality_pred' },
        { name: 'filter_by', label: 'Keep Labels', type: 'string_list', required: false, default: null },
        { name: 'score_field', label: 'Score Field', type: 'string', required: false, default: null },
    ],
};

export const DOMAIN_CLASSIFIER_TEMPLATE: NodeTemplate = {
    stageType: 'DomainClassifier',
    label: 'Domain Classifier',
    category: 'classifiers',
    headerColor: 'bg-purple-600',
    description: 'Classify documents into content domains (English)',
    params: [
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
        { name: 'label_field', label: 'Label Field', type: 'string', required: false, default: 'domain_pred' },
        { name: 'filter_by', label: 'Keep Labels', type: 'string_list', required: false, default: null },
        { name: 'score_field', label: 'Score Field', type: 'string', required: false, default: null },
    ],
};

export const MULTILINGUAL_DOMAIN_CLASSIFIER_TEMPLATE: NodeTemplate = {
    stageType: 'MultilingualDomainClassifier',
    label: 'Multilingual Domain Classifier',
    category: 'classifiers',
    headerColor: 'bg-purple-600',
    description: 'Classify documents into content domains (52 languages)',
    params: [
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
        { name: 'label_field', label: 'Label Field', type: 'string', required: false, default: 'multilingual_domain_pred' },
        { name: 'filter_by', label: 'Keep Labels', type: 'string_list', required: false, default: null },
        { name: 'score_field', label: 'Score Field', type: 'string', required: false, default: null },
    ],
};

export const CONTENT_TYPE_CLASSIFIER_TEMPLATE: NodeTemplate = {
    stageType: 'ContentTypeClassifier',
    label: 'Content Type Classifier',
    category: 'classifiers',
    headerColor: 'bg-purple-600',
    description: 'Classify documents into 11 content speech types',
    params: [
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
        { name: 'label_field', label: 'Label Field', type: 'string', required: false, default: 'content_pred' },
        { name: 'filter_by', label: 'Keep Labels', type: 'string_list', required: false, default: null },
        { name: 'score_field', label: 'Score Field', type: 'string', required: false, default: null },
    ],
};

export const FINEWEB_EDU_CLASSIFIER_TEMPLATE: NodeTemplate = {
    stageType: 'FineWebEduClassifier',
    label: 'FineWeb Edu Classifier',
    category: 'classifiers',
    headerColor: 'bg-purple-600',
    description: 'Score documents for educational content quality (0–5)',
    params: [
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
        { name: 'label_field', label: 'Label Field', type: 'string', required: false, default: 'fineweb-edu-score-label' },
        { name: 'float_score_field', label: 'Float Score Field', type: 'string', required: false, default: 'fineweb-edu-score-float' },
        { name: 'int_score_field', label: 'Int Score Field', type: 'string', required: false, default: 'fineweb-edu-score-int' },
        { name: 'filter_by', label: 'Keep Labels', type: 'string_list', required: false, default: null },
    ],
};

export const FINEWEB_MIXTRAL_EDU_CLASSIFIER_TEMPLATE: NodeTemplate = {
    stageType: 'FineWebMixtralEduClassifier',
    label: 'FineWeb Mixtral Edu Classifier',
    category: 'classifiers',
    headerColor: 'bg-purple-600',
    description: 'Score documents for educational quality using Mixtral annotations',
    params: [
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
        { name: 'label_field', label: 'Label Field', type: 'string', required: false, default: 'fineweb-mixtral-edu-score-label' },
        { name: 'float_score_field', label: 'Float Score Field', type: 'string', required: false, default: 'fineweb-mixtral-edu-score-float' },
        { name: 'int_score_field', label: 'Int Score Field', type: 'string', required: false, default: 'fineweb-mixtral-edu-score-int' },
        { name: 'filter_by', label: 'Keep Labels', type: 'string_list', required: false, default: null },
    ],
};

export const FINEWEB_NEMOTRON_EDU_CLASSIFIER_TEMPLATE: NodeTemplate = {
    stageType: 'FineWebNemotronEduClassifier',
    label: 'FineWeb Nemotron Edu Classifier',
    category: 'classifiers',
    headerColor: 'bg-purple-600',
    description: 'Score documents for educational quality using Nemotron-4 annotations',
    params: [
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
        { name: 'label_field', label: 'Label Field', type: 'string', required: false, default: 'fineweb-nemotron-edu-score-label' },
        { name: 'float_score_field', label: 'Float Score Field', type: 'string', required: false, default: 'fineweb-nemotron-edu-score-float' },
        { name: 'int_score_field', label: 'Int Score Field', type: 'string', required: false, default: 'fineweb-nemotron-edu-score-int' },
        { name: 'filter_by', label: 'Keep Labels', type: 'string_list', required: false, default: null },
    ],
};

export const PROMPT_TASK_COMPLEXITY_CLASSIFIER_TEMPLATE: NodeTemplate = {
    stageType: 'PromptTaskComplexityClassifier',
    label: 'Prompt Task & Complexity',
    category: 'classifiers',
    headerColor: 'bg-purple-600',
    description: 'Score prompts across 11 task types and 6 complexity dimensions',
    params: [
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
    ],
};


export const SYMBOLS_TO_WORDS_FILTER_TEMPLATE: NodeTemplate = {
    stageType: 'SymbolsToWordsFilter',
    label: 'Symbols to Words Filter',
    category: 'filters',
    headerColor: 'bg-amber-600',
    description: 'Remove docs with a high symbol-to-word ratio (hash/ellipsis)',
    params: [
        { name: 'max_symbol_to_word_ratio', label: 'Max Symbol/Word Ratio', type: 'number', required: false, default: 0.1 },
        { name: 'lang', label: 'Language', type: 'string', required: false, default: 'en' },
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
        { name: 'score_field', label: 'Score Field', type: 'string', required: false, default: null },
        { name: 'invert', label: 'Invert', type: 'boolean', required: false, default: false },
    ],
};

export const PARENTHESES_FILTER_TEMPLATE: NodeTemplate = {
    stageType: 'ParenthesesFilter',
    label: 'Parentheses Filter',
    category: 'filters',
    headerColor: 'bg-amber-600',
    description: 'Remove docs where too much text is wrapped in parentheses',
    params: [
        { name: 'max_parentheses_ratio', label: 'Max Parentheses Ratio', type: 'number', required: false, default: 0.1 },
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
        { name: 'score_field', label: 'Score Field', type: 'string', required: false, default: null },
        { name: 'invert', label: 'Invert', type: 'boolean', required: false, default: false },
    ],
};

export const MEAN_WORD_LENGTH_FILTER_TEMPLATE: NodeTemplate = {
    stageType: 'MeanWordLengthFilter',
    label: 'Mean Word Length Filter',
    category: 'filters',
    headerColor: 'bg-amber-600',
    description: 'Remove docs where average word length is outside a target range',
    params: [
        { name: 'min_mean_word_length', label: 'Min Mean Word Length', type: 'number', required: false, default: 3 },
        { name: 'max_mean_word_length', label: 'Max Mean Word Length', type: 'number', required: false, default: 10 },
        { name: 'lang', label: 'Language', type: 'string', required: false, default: 'en' },
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
        { name: 'score_field', label: 'Score Field', type: 'string', required: false, default: null },
        { name: 'invert', label: 'Invert', type: 'boolean', required: false, default: false },
    ],
};

export const PUNCTUATION_FILTER_TEMPLATE: NodeTemplate = {
    stageType: 'PunctuationFilter',
    label: 'Punctuation Filter',
    category: 'filters',
    headerColor: 'bg-amber-600',
    description: 'Remove docs where most sentences lack end punctuation',
    params: [
        { name: 'max_num_sentences_without_endmark_ratio', label: 'Max Sentences Without Endmark Ratio', type: 'number', required: false, default: 0.85 },
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
        { name: 'score_field', label: 'Score Field', type: 'string', required: false, default: null },
        { name: 'invert', label: 'Invert', type: 'boolean', required: false, default: false },
    ],
};

export const ELLIPSIS_FILTER_TEMPLATE: NodeTemplate = {
    stageType: 'EllipsisFilter',
    label: 'Ellipsis Filter',
    category: 'filters',
    headerColor: 'bg-amber-600',
    description: 'Remove docs where too many lines end with ellipsis',
    params: [
        { name: 'max_num_lines_ending_with_ellipsis_ratio', label: 'Max Ellipsis Line Ratio', type: 'number', required: false, default: 0.3 },
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
        { name: 'score_field', label: 'Score Field', type: 'string', required: false, default: null },
        { name: 'invert', label: 'Invert', type: 'boolean', required: false, default: false },
    ],
};

export const COMMON_ENGLISH_WORDS_FILTER_TEMPLATE: NodeTemplate = {
    stageType: 'CommonEnglishWordsFilter',
    label: 'Common English Words Filter',
    category: 'filters',
    headerColor: 'bg-amber-600',
    description: 'Remove docs that contain fewer than N common English words',
    params: [
        { name: 'min_num_common_words', label: 'Min Common Words', type: 'number', required: false, default: 2 },
        { name: 'stop_at_false', label: 'Stop at False', type: 'boolean', required: false, default: true },
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
        { name: 'score_field', label: 'Score Field', type: 'string', required: false, default: null },
        { name: 'invert', label: 'Invert', type: 'boolean', required: false, default: false },
    ],
};

export const WORDS_WITHOUT_ALPHABETS_FILTER_TEMPLATE: NodeTemplate = {
    stageType: 'WordsWithoutAlphabetsFilter',
    label: 'Words Without Alphabets Filter',
    category: 'filters',
    headerColor: 'bg-amber-600',
    description: 'Remove docs where too few words contain alphabetic characters',
    params: [
        { name: 'min_words_with_alphabets', label: 'Min Words With Alphabets', type: 'number', required: false, default: 0.8 },
        { name: 'lang', label: 'Language', type: 'string', required: false, default: 'en' },
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
        { name: 'score_field', label: 'Score Field', type: 'string', required: false, default: null },
        { name: 'invert', label: 'Invert', type: 'boolean', required: false, default: false },
    ],
};

export const PORNOGRAPHIC_URLS_FILTER_TEMPLATE: NodeTemplate = {
    stageType: 'PornographicUrlsFilter',
    label: 'Pornographic URLs Filter',
    category: 'filters',
    headerColor: 'bg-amber-600',
    description: 'Remove docs containing URLs that point to adult content',
    params: [
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
        { name: 'score_field', label: 'Score Field', type: 'string', required: false, default: null },
        { name: 'invert', label: 'Invert', type: 'boolean', required: false, default: false },
    ],
};

export const SUBSTRING_FILTER_TEMPLATE: NodeTemplate = {
    stageType: 'SubstringFilter',
    label: 'Substring Filter',
    category: 'filters',
    headerColor: 'bg-amber-600',
    description: 'Keep docs that contain a given substring at a specified position',
    params: [
        { name: 'substring', label: 'Substring', type: 'string', required: true },
        { name: 'position', label: 'Position', type: 'select', required: true, default: 'any', options: ['prefix', 'suffix', 'any'] },
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
        { name: 'score_field', label: 'Score Field', type: 'string', required: false, default: null },
        { name: 'invert', label: 'Invert', type: 'boolean', required: false, default: false },
    ],
};

export const REPEATED_LINES_FILTER_TEMPLATE: NodeTemplate = {
    stageType: 'RepeatedLinesFilter',
    label: 'Repeated Lines Filter',
    category: 'filters',
    headerColor: 'bg-amber-600',
    description: 'Remove docs that shrink significantly after deduplicating lines',
    params: [
        { name: 'max_repeated_line_fraction', label: 'Max Repeated Line Fraction', type: 'number', required: false, default: 0.7 },
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
        { name: 'score_field', label: 'Score Field', type: 'string', required: false, default: null },
        { name: 'invert', label: 'Invert', type: 'boolean', required: false, default: false },
    ],
};

export const REPEATED_PARAGRAPHS_FILTER_TEMPLATE: NodeTemplate = {
    stageType: 'RepeatedParagraphsFilter',
    label: 'Repeated Paragraphs Filter',
    category: 'filters',
    headerColor: 'bg-amber-600',
    description: 'Remove docs that shrink significantly after deduplicating paragraphs',
    params: [
        { name: 'max_repeated_paragraphs_ratio', label: 'Max Repeated Paragraphs Ratio', type: 'number', required: false, default: 0.7 },
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
        { name: 'score_field', label: 'Score Field', type: 'string', required: false, default: null },
        { name: 'invert', label: 'Invert', type: 'boolean', required: false, default: false },
    ],
};

export const REPEATED_LINES_BY_CHAR_FILTER_TEMPLATE: NodeTemplate = {
    stageType: 'RepeatedLinesByCharFilter',
    label: 'Repeated Lines by Char Filter',
    category: 'filters',
    headerColor: 'bg-amber-600',
    description: 'Remove docs with high repeated-line character ratio',
    params: [
        { name: 'max_repeated_lines_char_ratio', label: 'Max Repeated Lines Char Ratio', type: 'number', required: false, default: 0.8 },
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
        { name: 'score_field', label: 'Score Field', type: 'string', required: false, default: null },
        { name: 'invert', label: 'Invert', type: 'boolean', required: false, default: false },
    ],
};

export const REPEATED_PARAGRAPHS_BY_CHAR_FILTER_TEMPLATE: NodeTemplate = {
    stageType: 'RepeatedParagraphsByCharFilter',
    label: 'Repeated Paragraphs by Char Filter',
    category: 'filters',
    headerColor: 'bg-amber-600',
    description: 'Remove docs with high repeated-paragraph character ratio',
    params: [
        { name: 'max_repeated_paragraphs_char_ratio', label: 'Max Repeated Paragraphs Char Ratio', type: 'number', required: false, default: 0.8 },
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
        { name: 'score_field', label: 'Score Field', type: 'string', required: false, default: null },
        { name: 'invert', label: 'Invert', type: 'boolean', required: false, default: false },
    ],
};

export const REPEATING_TOP_NGRAMS_FILTER_TEMPLATE: NodeTemplate = {
    stageType: 'RepeatingTopNGramsFilter',
    label: 'Repeating Top N-Grams Filter',
    category: 'filters',
    headerColor: 'bg-amber-600',
    description: 'Remove docs where top n-grams dominate the character count',
    params: [
        { name: 'n', label: 'N-Gram Size', type: 'number', required: false, default: 2 },
        { name: 'max_repeating_ngram_ratio', label: 'Max Repeating N-Gram Ratio', type: 'number', required: false, default: 0.2 },
        { name: 'lang', label: 'Language', type: 'string', required: false, default: 'en' },
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
        { name: 'score_field', label: 'Score Field', type: 'string', required: false, default: null },
        { name: 'invert', label: 'Invert', type: 'boolean', required: false, default: false },
    ],
};

export const REPEATING_DUPLICATE_NGRAMS_FILTER_TEMPLATE: NodeTemplate = {
    stageType: 'RepeatingDuplicateNGramsFilter',
    label: 'Repeating Duplicate N-Grams Filter',
    category: 'filters',
    headerColor: 'bg-amber-600',
    description: 'Remove docs where duplicate n-grams dominate the character count',
    params: [
        { name: 'n', label: 'N-Gram Size', type: 'number', required: false, default: 2 },
        { name: 'max_repeating_duplicate_ngram_ratio', label: 'Max Duplicate N-Gram Ratio', type: 'number', required: false, default: 0.2 },
        { name: 'lang', label: 'Language', type: 'string', required: false, default: 'en' },
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
        { name: 'score_field', label: 'Score Field', type: 'string', required: false, default: null },
        { name: 'invert', label: 'Invert', type: 'boolean', required: false, default: false },
    ],
};

export const EXACT_DEDUP_TEMPLATE: NodeTemplate = {
    stageType: 'ExactDedup',
    label: 'Exact Dedup',
    category: 'deduplication',
    headerColor: 'bg-cyan-700',
    description: 'Remove exact duplicate documents using hash-based identification (GPU)',
    params: [
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
        { name: 'assign_id', label: 'Auto-assign IDs', type: 'boolean', required: false, default: true },
    ],
};

export const FUZZY_DEDUP_TEMPLATE: NodeTemplate = {
    stageType: 'FuzzyDedup',
    label: 'Fuzzy Dedup',
    category: 'deduplication',
    headerColor: 'bg-cyan-700',
    description: 'Remove near-duplicate documents using MinHash/LSH (GPU)',
    params: [
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
        { name: 'char_ngrams', label: 'Char N-gram Size', type: 'number', required: false, default: 24 },
        { name: 'num_bands', label: 'LSH Bands', type: 'number', required: false, default: 20 },
        { name: 'minhashes_per_band', label: 'Hashes per Band', type: 'number', required: false, default: 13 },
        { name: 'use_64_bit_hash', label: '64-bit Hash', type: 'boolean', required: false, default: false },
        { name: 'seed', label: 'Seed', type: 'number', required: false, default: 42 },
    ],
};


export const PYTHON_COMMENT_TO_CODE_FILTER_TEMPLATE: NodeTemplate = {
    stageType: 'PythonCommentToCodeFilter',
    label: 'Python Comment/Code Ratio',
    category: 'filters',
    headerColor: 'bg-violet-700',
    description: 'Filter Python files by comment-to-code ratio',
    params: [
        { name: 'min_comment_to_code_ratio', label: 'Min Comment Ratio', type: 'number', required: false, default: 0.01 },
        { name: 'max_comment_to_code_ratio', label: 'Max Comment Ratio', type: 'number', required: false, default: 0.85 },
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
        { name: 'score_field', label: 'Score Field', type: 'string', required: false, default: null },
        { name: 'invert', label: 'Invert', type: 'boolean', required: false, default: false },
    ],
};

export const GENERAL_COMMENT_TO_CODE_FILTER_TEMPLATE: NodeTemplate = {
    stageType: 'GeneralCommentToCodeFilter',
    label: 'Comment/Code Ratio',
    category: 'filters',
    headerColor: 'bg-violet-700',
    description: 'Filter code files by comment ratio (any language via MIME type)',
    params: [
        { name: 'language', label: 'Language (MIME)', type: 'string', required: true },
        { name: 'min_comment_to_code_ratio', label: 'Min Comment Ratio', type: 'number', required: false, default: 0.01 },
        { name: 'max_comment_to_code_ratio', label: 'Max Comment Ratio', type: 'number', required: false, default: 0.85 },
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
        { name: 'score_field', label: 'Score Field', type: 'string', required: false, default: null },
        { name: 'invert', label: 'Invert', type: 'boolean', required: false, default: false },
    ],
};

export const NUMBER_OF_LINES_OF_CODE_FILTER_TEMPLATE: NodeTemplate = {
    stageType: 'NumberOfLinesOfCodeFilter',
    label: 'Lines of Code',
    category: 'filters',
    headerColor: 'bg-violet-700',
    description: 'Filter by number of lines of code',
    params: [
        { name: 'min_lines', label: 'Min Lines', type: 'number', required: false, default: 10 },
        { name: 'max_lines', label: 'Max Lines', type: 'number', required: false, default: 20000 },
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
        { name: 'score_field', label: 'Score Field', type: 'string', required: false, default: null },
        { name: 'invert', label: 'Invert', type: 'boolean', required: false, default: false },
    ],
};

export const XML_HEADER_FILTER_TEMPLATE: NodeTemplate = {
    stageType: 'XMLHeaderFilter',
    label: 'XML Header',
    category: 'filters',
    headerColor: 'bg-violet-700',
    description: 'Remove files with XML headers (likely wrong extension)',
    params: [
        { name: 'char_prefix_search_length', label: 'Prefix Search Length', type: 'number', required: false, default: 100 },
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
        { name: 'score_field', label: 'Score Field', type: 'string', required: false, default: null },
        { name: 'invert', label: 'Invert', type: 'boolean', required: false, default: false },
    ],
};

export const ALPHA_FILTER_TEMPLATE: NodeTemplate = {
    stageType: 'AlphaFilter',
    label: 'Alpha Ratio',
    category: 'filters',
    headerColor: 'bg-violet-700',
    description: 'Filter out files that are mostly non-alphabetic (e.g. raw tensors or tables)',
    params: [
        { name: 'min_alpha_ratio', label: 'Min Alpha Ratio', type: 'number', required: false, default: 0.25 },
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
        { name: 'score_field', label: 'Score Field', type: 'string', required: false, default: null },
        { name: 'invert', label: 'Invert', type: 'boolean', required: false, default: false },
    ],
};

export const HTML_BOILERPLATE_FILTER_TEMPLATE: NodeTemplate = {
    stageType: 'HTMLBoilerplateFilter',
    label: 'HTML Boilerplate',
    category: 'filters',
    headerColor: 'bg-violet-700',
    description: 'Remove HTML files that are mostly boilerplate script/style with little visible text',
    params: [
        { name: 'min_lang_content_ratio', label: 'Min Content Ratio', type: 'number', required: false, default: 0.2 },
        { name: 'min_lang_content_num_chars', label: 'Min Content Chars', type: 'number', required: false, default: 100 },
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
        { name: 'score_field', label: 'Score Field', type: 'string', required: false, default: null },
        { name: 'invert', label: 'Invert', type: 'boolean', required: false, default: false },
    ],
};

export const FASTTEXT_QUALITY_FILTER_TEMPLATE: NodeTemplate = {
    stageType: 'FastTextQualityFilter',
    label: 'FastText Quality',
    category: 'filters',
    headerColor: 'bg-orange-600',
    description: 'Filter documents by quality score using a FastText model',
    params: [
        { name: 'model_path', label: 'Model Path', type: 'string', required: true },
        { name: 'label', label: 'Label', type: 'string', required: false, default: '__label__hq' },
        { name: 'alpha', label: 'Alpha (Pareto)', type: 'number', required: false, default: 3 },
        { name: 'seed', label: 'Seed', type: 'number', required: false, default: 42 },
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
        { name: 'score_field', label: 'Score Field', type: 'string', required: false, default: null },
        { name: 'invert', label: 'Invert', type: 'boolean', required: false, default: false },
    ],
};

export const FASTTEXT_LANG_ID_TEMPLATE: NodeTemplate = {
    stageType: 'FastTextLangId',
    label: 'FastText Language ID',
    category: 'filters',
    headerColor: 'bg-orange-600',
    description: 'Filter documents by detected language using FastText lid.176 model',
    params: [
        { name: 'model_path', label: 'Model Path', type: 'string', required: false, default: '/workspace/curator/cache/hf-hub/fasttext/lid.176.bin' },
        { name: 'min_langid_score', label: 'Min Confidence', type: 'number', required: false, default: 0.3 },
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
        { name: 'score_field', label: 'Score Field', type: 'string', required: false, default: null },
        { name: 'invert', label: 'Invert', type: 'boolean', required: false, default: false },
    ],
};

export const FASTTEXT_LABEL_MODIFIER_TEMPLATE: NodeTemplate = {
    stageType: 'FastTextLabelModifier',
    label: 'FastText Label',
    category: 'modifiers',
    headerColor: 'bg-orange-600',
    description: 'Prepend a FastText label prefix to each document (e.g. for training data)',
    params: [
        { name: 'label', label: 'Label', type: 'string', required: true },
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
    ],
};

export const HISTOGRAM_FILTER_TEMPLATE: NodeTemplate = {
    stageType: 'HistogramFilter',
    label: 'Histogram Filter',
    category: 'filters',
    headerColor: 'bg-indigo-600',
    description: 'Filter by character coverage histogram (multi-language, auto-downloads on first use)',
    params: [
        { name: 'lang', label: 'Language Code', type: 'string', required: false, default: 'en' },
        { name: 'threshold', label: 'Coverage Threshold', type: 'number', required: false, default: 0.8 },
        { name: 'cache_dir', label: 'Cache Dir', type: 'string', required: false, default: '' },
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
        { name: 'score_field', label: 'Score Field', type: 'string', required: false, default: null },
        { name: 'invert', label: 'Invert', type: 'boolean', required: false, default: false },
    ],
};

export const TOKEN_COUNT_FILTER_TEMPLATE: NodeTemplate = {
    stageType: 'TokenCountFilter',
    label: 'Token Count',
    category: 'filters',
    headerColor: 'bg-indigo-600',
    description: 'Filter documents by tokenized length using a HuggingFace tokenizer',
    params: [
        { name: 'hf_model_name', label: 'HF Model Name', type: 'string', required: true },
        { name: 'hf_token', label: 'HF Token', type: 'string', required: false, default: null },
        { name: 'min_tokens', label: 'Min Tokens', type: 'number', required: false, default: 0 },
        { name: 'max_tokens', label: 'Max Tokens', type: 'number', required: false, default: null },
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
        { name: 'score_field', label: 'Score Field', type: 'string', required: false, default: null },
        { name: 'invert', label: 'Invert', type: 'boolean', required: false, default: false },
    ],
};

export const TOKENIZER_FERTILITY_FILTER_TEMPLATE: NodeTemplate = {
    stageType: 'TokenizerFertilityFilter',
    label: 'Tokenizer Fertility',
    category: 'filters',
    headerColor: 'bg-violet-700',
    description: 'Filter code by chars-per-token ratio using a SentencePiece tokenizer',
    params: [
        { name: 'path_to_tokenizer', label: 'Tokenizer Path (.model)', type: 'string', required: true },
        { name: 'min_char_to_token_ratio', label: 'Min Char/Token Ratio', type: 'number', required: false, default: 2.5 },
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
        { name: 'score_field', label: 'Score Field', type: 'string', required: false, default: null },
        { name: 'invert', label: 'Invert', type: 'boolean', required: false, default: false },
    ],
};

export const PER_EXTENSION_FILTER_TEMPLATE: NodeTemplate = {
    stageType: 'PerExtensionFilter',
    label: 'Per-Extension Filter',
    category: 'filters',
    headerColor: 'bg-violet-700',
    description: 'Apply language/extension-specific code quality rules from a metadata CSV',
    params: [
        { name: 'lang', label: 'Language (lowercase, e.g. python)', type: 'string', required: true },
        { name: 'extension', label: 'Extension (e.g. py)', type: 'string', required: true },
        { name: 'metadata_file', label: 'Metadata CSV', type: 'string', required: false, default: '/app/nemo_curator/utils/code_meta.csv' },
        { name: 'text_field', label: 'Text Field', type: 'string', required: false, default: 'text' },
        { name: 'score_field', label: 'Score Field', type: 'string', required: false, default: null },
        { name: 'invert', label: 'Invert', type: 'boolean', required: false, default: false },
    ],
};

export const ALL_NODE_TEMPLATES: NodeTemplate[] = [
    DOCUMENT_JOINER_TEMPLATE,
    DOCUMENT_SPLITTER_TEMPLATE,
    WORD_COUNT_FILTER_TEMPLATE,
    NON_ALPHA_NUMERIC_FILTER_TEMPLATE,
    URLS_FILTER_TEMPLATE,
    NUMBERS_FILTER_TEMPLATE,
    WHITESPACE_FILTER_TEMPLATE,
    BULLETS_FILTER_TEMPLATE,
    LONG_WORD_FILTER_TEMPLATE,
    BOILERPLATE_STRING_FILTER_TEMPLATE,
    SYMBOLS_TO_WORDS_FILTER_TEMPLATE,
    PARENTHESES_FILTER_TEMPLATE,
    MEAN_WORD_LENGTH_FILTER_TEMPLATE,
    PUNCTUATION_FILTER_TEMPLATE,
    ELLIPSIS_FILTER_TEMPLATE,
    COMMON_ENGLISH_WORDS_FILTER_TEMPLATE,
    WORDS_WITHOUT_ALPHABETS_FILTER_TEMPLATE,
    PORNOGRAPHIC_URLS_FILTER_TEMPLATE,
    SUBSTRING_FILTER_TEMPLATE,
    REPEATED_LINES_FILTER_TEMPLATE,
    REPEATED_PARAGRAPHS_FILTER_TEMPLATE,
    REPEATED_LINES_BY_CHAR_FILTER_TEMPLATE,
    REPEATED_PARAGRAPHS_BY_CHAR_FILTER_TEMPLATE,
    REPEATING_TOP_NGRAMS_FILTER_TEMPLATE,
    REPEATING_DUPLICATE_NGRAMS_FILTER_TEMPLATE,
    BOILERPLATE_STRING_MODIFIER_TEMPLATE,
    QUOTATION_REMOVER_MODIFIER_TEMPLATE,
    MARKDOWN_REMOVER_MODIFIER_TEMPLATE,
    NEWLINE_NORMALIZER_MODIFIER_TEMPLATE,
    SLICER_MODIFIER_TEMPLATE,
    URL_REMOVER_MODIFIER_TEMPLATE,
    LINE_REMOVER_MODIFIER_TEMPLATE,
    UNICODE_REFORMATTER_MODIFIER_TEMPLATE,
    QUALITY_CLASSIFIER_TEMPLATE,
    DOMAIN_CLASSIFIER_TEMPLATE,
    MULTILINGUAL_DOMAIN_CLASSIFIER_TEMPLATE,
    CONTENT_TYPE_CLASSIFIER_TEMPLATE,
    FINEWEB_EDU_CLASSIFIER_TEMPLATE,
    FINEWEB_MIXTRAL_EDU_CLASSIFIER_TEMPLATE,
    FINEWEB_NEMOTRON_EDU_CLASSIFIER_TEMPLATE,
    PROMPT_TASK_COMPLEXITY_CLASSIFIER_TEMPLATE,
    EXACT_DEDUP_TEMPLATE,
    FUZZY_DEDUP_TEMPLATE,
    PYTHON_COMMENT_TO_CODE_FILTER_TEMPLATE,
    GENERAL_COMMENT_TO_CODE_FILTER_TEMPLATE,
    NUMBER_OF_LINES_OF_CODE_FILTER_TEMPLATE,
    XML_HEADER_FILTER_TEMPLATE,
    ALPHA_FILTER_TEMPLATE,
    HTML_BOILERPLATE_FILTER_TEMPLATE,
    TOKENIZER_FERTILITY_FILTER_TEMPLATE,
    PER_EXTENSION_FILTER_TEMPLATE,
    FASTTEXT_QUALITY_FILTER_TEMPLATE,
    FASTTEXT_LANG_ID_TEMPLATE,
    FASTTEXT_LABEL_MODIFIER_TEMPLATE,
    HISTOGRAM_FILTER_TEMPLATE,
    TOKEN_COUNT_FILTER_TEMPLATE,
];

export const TEMPLATES_BY_STAGE_TYPE: Record<string, NodeTemplate> = Object.fromEntries(
    ALL_NODE_TEMPLATES.map((t) => [t.stageType, t])
);
