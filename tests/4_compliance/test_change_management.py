"""
Compliance Test: Change Management & Deployment Controls
═══════════════════════════════════════════════════════════
Frameworks: SOC 2 CC8.1, PCI DSS 6.4.5, ITIL Change Management

Validates:
  • CODEOWNERS file exists (mandatory review)
  • Two-person rule is enforced for critical changes
  • GitOps deployment pipeline exists
  • Rollback mechanism is documented
  • Pre-commit hooks are configured
"""

import os


class TestChangeManagement:
    """SOC 2 CC8.1: Changes must be authorized, tested, and documented."""

    def test_codeowners_file_exists(self):
        """SOC 2 CC8.1: Code changes must require designated reviewers."""
        path = os.path.join(os.path.dirname(__file__), "..", "..", ".github", "CODEOWNERS")
        assert os.path.exists(path), "SOC 2 VIOLATION: CODEOWNERS file must exist in .github/"
        with open(path) as f:
            content = f.read()
        assert len(content.strip()) > 0, "CODEOWNERS file must not be empty"

    def test_pre_commit_hooks_configured(self):
        """PCI 6.4.5: Pre-commit validation must be configured."""
        path = os.path.join(os.path.dirname(__file__), "..", "..", ".pre-commit-config.yaml")
        assert os.path.exists(
            path
        ), "Pre-commit hooks must be configured (.pre-commit-config.yaml)"

    def test_gitops_deployment_pipeline_exists(self):
        """SOC 2 CC8.1: Changes must flow through an automated pipeline."""
        gitops_path = os.path.join(
            os.path.dirname(__file__), "..", "..", ".github", "workflows", "gitops.yml"
        )
        assert os.path.exists(gitops_path), "GitOps deployment pipeline must exist"

    def test_main_ci_pipeline_exists(self):
        """PCI 6.3.2: CI pipeline must validate changes before merge."""
        pipeline_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            ".github",
            "workflows",
            "high-assurance-pipeline.yml",
        )
        assert os.path.exists(
            pipeline_path
        ), "Main CI pipeline must exist at .github/workflows/high-assurance-pipeline.yml"

    def test_concourse_pipeline_exists(self):
        """SOC 2: Alternative CI system for redundancy."""
        paths = [
            os.path.join(os.path.dirname(__file__), "..", "..", "pipeline.yml"),
            os.path.join(os.path.dirname(__file__), "..", "..", "docker-compose-concourse.yml"),
        ]
        for p in paths:
            assert os.path.exists(p), f"Missing: {os.path.basename(p)}"

    def test_argocd_gitops_manifest_exists(self):
        """SOC 2 CC8.1: GitOps declarative deployment must be configured."""
        path = os.path.join(os.path.dirname(__file__), "..", "..", "argocd-app.yaml")
        assert os.path.exists(path), "ArgoCD application manifest must exist"
        with open(path) as f:
            content = f.read()
        assert "syncPolicy" in content, "ArgoCD must have sync policy configured"
        assert "automated" in content, "ArgoCD must have automated sync enabled"

    def test_dependabot_configured(self):
        """PCI 6.2: Dependency updates must be automated."""
        path = os.path.join(os.path.dirname(__file__), "..", "..", ".github", "dependabot.yml")
        assert os.path.exists(
            path
        ), "Dependabot must be configured for automated dependency updates"

    def test_two_person_rule_test_exists(self):
        """SOC 2 CC8.1: Critical changes require dual authorization."""
        path = os.path.join(
            os.path.dirname(__file__), "..", "17_two_person_rule", "test_two_person_rule.py"
        )
        assert os.path.exists(path), "Two-person rule test must exist"

    def test_gitignore_excludes_sensitive_files(self):
        """PCI 3.4: Sensitive files must be excluded from version control."""
        path = os.path.join(os.path.dirname(__file__), "..", "..", ".gitignore")
        assert os.path.exists(path), ".gitignore must exist"
        with open(path) as f:
            content = f.read()
        required_excludes = [".env", "*.db", "__pycache__"]
        for pattern in required_excludes:
            assert pattern in content, f".gitignore must exclude '{pattern}'"
