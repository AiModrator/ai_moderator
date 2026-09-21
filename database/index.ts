import { prisma } from './prismaClient.js';
import {
  Account as AccountModel,
  Community as CommunityModel,
  ApiKey as ApiKeyModel,
  Workflow as WorkflowModel,
  Rule as RuleModel,
  $Enums,
} from './generated/client.js';

export default prisma;
export { checkDbConnection } from './prismaClient.js';

export type Account = AccountModel;
export type Community = CommunityModel;
export type ApiKey = ApiKeyModel;
export type Workflow = WorkflowModel;
export type Rule = RuleModel;

export type RiskClass = $Enums.RiskClass;
export type Severity = $Enums.Severity;
export type ContentAction = $Enums.ContentAction;
export type UserAction = $Enums.UserAction;

export const RiskClass = $Enums.RiskClass;
export const Severity = $Enums.Severity;
export const ContentAction = $Enums.ContentAction;
export const UserAction = $Enums.UserAction;