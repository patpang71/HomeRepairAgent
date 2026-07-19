import * as cdk from 'aws-cdk-lib';
import * as bedrock from 'aws-cdk-lib/aws-bedrock';
import { Construct } from 'constructs';
import { AWS_REGION, GUARDRAIL_GROUNDING_THRESHOLD, GUARDRAIL_RELEVANCE_THRESHOLD } from './constants';

export class GuardrailStack extends cdk.Stack {
  public readonly guardrail: bedrock.CfnGuardrail;
  public readonly guardrailVersion: bedrock.CfnGuardrailVersion;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, { ...props, env: { ...props?.env, region: AWS_REGION } });

    this.guardrail = new bedrock.CfnGuardrail(this, 'Guardrail', {
      name: 'HomeRepairAgentGuardrail',
      description: 'Profanity filtering, PII protection, and RAG grounding checks for the home repair agent.',
      blockedInputMessaging: "I can't respond to that — let's stick to home repair questions.",
      blockedOutputsMessaging: "I'm not able to share that response — could you rephrase your question?",

      // Built-in profanity list — no need to source/maintain our own word list.
      wordPolicyConfig: {
        managedWordListsConfig: [
          { type: 'PROFANITY' },
        ],
      },

      // Protect against the model echoing back sensitive data. EMAIL/PHONE are masked
      // rather than blocked since they can plausibly show up in legitimate conversation
      // (e.g. contact info); financial/credential identifiers are hard-blocked outright.
      // NAME and ADDRESS are intentionally excluded — this app legitimately discusses
      // project addresses and user names as part of normal conversation, and blocking or
      // masking those would break the core home-repair flow.
      sensitiveInformationPolicyConfig: {
        piiEntitiesConfig: [
          { type: 'EMAIL', action: 'ANONYMIZE' },
          { type: 'PHONE', action: 'ANONYMIZE' },
          { type: 'US_SOCIAL_SECURITY_NUMBER', action: 'BLOCK' },
          { type: 'CREDIT_DEBIT_CARD_NUMBER', action: 'BLOCK' },
          { type: 'US_BANK_ACCOUNT_NUMBER', action: 'BLOCK' },
          { type: 'PASSWORD', action: 'BLOCK' },
          { type: 'AWS_ACCESS_KEY', action: 'BLOCK' },
          { type: 'AWS_SECRET_KEY', action: 'BLOCK' },
        ],
      },

      // Flags model responses that aren't backed by the retrieved KB/Tavily search
      // context (grounding) or that don't actually answer the user's question (relevance).
      contextualGroundingPolicyConfig: {
        filtersConfig: [
          { type: 'GROUNDING', threshold: GUARDRAIL_GROUNDING_THRESHOLD, action: 'BLOCK', enabled: true },
          { type: 'RELEVANCE', threshold: GUARDRAIL_RELEVANCE_THRESHOLD, action: 'BLOCK', enabled: true },
        ],
      },
    });

    // Publish an immutable numbered version — the agent Lambda pins to this rather than DRAFT.
    this.guardrailVersion = new bedrock.CfnGuardrailVersion(this, 'GuardrailVersion', {
      guardrailIdentifier: this.guardrail.attrGuardrailId,
      description: 'Profanity + sensitive info + contextual grounding',
    });

    new cdk.CfnOutput(this, 'GuardrailId', {
      value: this.guardrail.attrGuardrailId,
      exportName: 'HomeRepairGuardrailId',
    });

    new cdk.CfnOutput(this, 'GuardrailVersionOutput', {
      value: this.guardrailVersion.attrVersion,
      exportName: 'HomeRepairGuardrailVersion',
    });
  }
}
