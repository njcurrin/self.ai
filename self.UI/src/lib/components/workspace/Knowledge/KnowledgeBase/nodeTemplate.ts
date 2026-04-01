export type ParamDef = {
    name: string;
    label: string;
    type: 'string' | 'number' | 'boolean';
    required: boolean;
    default?: string | number | boolean | null
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

export const ALL_NODE_TEMPLATES: NodeTemplate[] = [
    DOCUMENT_JOINER_TEMPLATE,
    DOCUMENT_SPLITTER_TEMPLATE,
];

export const TEMPLATES_BY_STAGE_TYPE: Record<string, NodeTemplate> = Object.fromEntries(
    ALL_NODE_TEMPLATES.map((t) => [t.stageType, t])
);
