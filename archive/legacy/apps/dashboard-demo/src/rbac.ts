/**
 * ═══════════════════════════════════════════════════
 * CITADEL RBAC — Role-Based Access Control
 * ═══════════════════════════════════════════════════
 *
 * Permission Matrix:
 * ┌───────────┬──────────────┬───────────┬──────────────┬────────────┐
 * │ Role      │Activate Agent│Activate NS│Activate Org  │Deactivate  │
 * ├───────────┼──────────────┼───────────┼──────────────┼────────────┤
 * │ Operator  │ Own only     │ No        │ No           │ Own only   │
 * │ Admin     │ Any agent    │ Yes       │ No           │Any except  │
 * │           │              │           │              │org-wide    │
 * │ Executive │ Any agent    │ Yes       │ Yes          │ Any        │
 * │ Auditor   │ View only    │ View only │ View only    │ No         │
 * └───────────┴──────────────┴───────────┴──────────────┴────────────┘
 *
 * AWS INTEGRATION STRATEGY:
 * ───────────────────────
 * Option A: Application-Level RBAC (Recommended)
 *   - Citadel manages its own roles/permissions via PostgreSQL RLS
 *   - JWT token contains `role` claim (issued by Citadel Auth or Cognito)
 *   - Backend enforces at middleware layer
 *   - Fastest to implement, full control
 *
 * Option B: AWS Cognito + IAM (Enterprise)
 *   - AWS Cognito User Pools for authentication
 *   - Cognito Groups map to Citadel roles (Operator/Admin/Executive/Auditor)
 *   - JWT from Cognito contains `cognito:groups` claim
 *   - API Gateway authorizer validates token + group membership
 *   - Can add IAM conditions for resource-level access
 *
 * Option C: AWS Organizations (Multi-Tenant)
 *   - Each Citadel "Organization" maps to an AWS Organization
 *   - SCPs (Service Control Policies) constrain what each org can do
 *   - Cross-account role assumption for namespace isolation
 *   - Best for enterprises already in AWS
 *
 * RECOMMENDED HYBRID:
 *   - Auth: AWS Cognito (federated SSO, MFA, password policies)
 *   - Authorization: Application-level RBAC (the code below)
 *   - Tenant Isolation: PostgreSQL RLS + org_id column
 *   - Audit: CloudTrail + Citadel's own hash-chained audit log
 */

export type CitadelRole = "operator" | "admin" | "executive" | "auditor";

export interface RBACPermissions {
  /* ── Agent Management ── */
  canActivateOwnAgent: boolean;
  canActivateAnyAgent: boolean;
  canDeactivateOwnAgent: boolean;
  canDeactivateAnyAgent: boolean;
  canDeactivateOrgWide: boolean;

  /* ── Namespace & Organization ── */
  canActivateNamespace: boolean;
  canActivateOrganization: boolean;

  /* ── General ── */
  canView: boolean;
  canEdit: boolean;
  canManageUsers: boolean;
  canExportAudit: boolean;
  canSeeKillSwitch: boolean;
  canTriggerKillSwitch: boolean;
  canAccessBilling: boolean;    // Executive only
  canOrgKillSwitch: boolean;     // Executive only — org-wide emergency
}

const PERMISSION_MATRIX: Record<CitadelRole, RBACPermissions> = {
  operator: {
    canActivateOwnAgent: true, canActivateAnyAgent: false,
    canDeactivateOwnAgent: true, canDeactivateAnyAgent: false, canDeactivateOrgWide: false,
    canActivateNamespace: false, canActivateOrganization: false,
    canView: true, canEdit: false, canManageUsers: false, canExportAudit: false,
    canSeeKillSwitch: true, canTriggerKillSwitch: false,
    canAccessBilling: false, canOrgKillSwitch: false,
  },
  admin: {
    canActivateOwnAgent: true, canActivateAnyAgent: true,
    canDeactivateOwnAgent: true, canDeactivateAnyAgent: true, canDeactivateOrgWide: false,
    canActivateNamespace: true, canActivateOrganization: false,
    canView: true, canEdit: true, canManageUsers: true, canExportAudit: true,
    canSeeKillSwitch: true, canTriggerKillSwitch: true,
    canAccessBilling: false, canOrgKillSwitch: false,
  },
  executive: {
    canActivateOwnAgent: true, canActivateAnyAgent: true,
    canDeactivateOwnAgent: true, canDeactivateAnyAgent: true, canDeactivateOrgWide: true,
    canActivateNamespace: true, canActivateOrganization: true,
    canView: true, canEdit: true, canManageUsers: true, canExportAudit: true,
    canSeeKillSwitch: true, canTriggerKillSwitch: true,
    canAccessBilling: true, canOrgKillSwitch: true,
  },
  auditor: {
    canActivateOwnAgent: false, canActivateAnyAgent: false,
    canDeactivateOwnAgent: false, canDeactivateAnyAgent: false, canDeactivateOrgWide: false,
    canActivateNamespace: false, canActivateOrganization: false,
    canView: true, canEdit: false, canManageUsers: false, canExportAudit: true,
    canSeeKillSwitch: true, canTriggerKillSwitch: false,
    canAccessBilling: false, canOrgKillSwitch: false,
  },
};

export function getPermissions(role: CitadelRole): RBACPermissions {
  return PERMISSION_MATRIX[role];
}

export function getRoleLabel(role: CitadelRole): string {
  const labels: Record<CitadelRole, string> = {
    operator: "Operator",
    admin: "Admin",
    executive: "Executive",
    auditor: "Auditor",
  };
  return labels[role];
}

export function getRoleColor(role: CitadelRole): string {
  const colors: Record<CitadelRole, string> = {
    operator: "bg-blue-100 text-blue-700 border-blue-200",
    admin: "bg-purple-100 text-purple-700 border-purple-200",
    executive: "bg-amber-100 text-amber-700 border-amber-200",
    auditor: "bg-slate-100 text-slate-700 border-slate-200",
  };
  return colors[role];
}

export function getRoleDescription(role: CitadelRole): string {
  const desc: Record<CitadelRole, string> = {
    operator: "Own agents only. Cannot trigger kill switch.",
    admin: "Any agent + namespace. No billing or org-wide.",
    executive: "Full access. Billing, org-wide, all actions.",
    auditor: "View-only access. Can export audit evidence.",
  };
  return desc[role];
}

export function isExecutive(role: CitadelRole): boolean {
  return role === "executive";
}
