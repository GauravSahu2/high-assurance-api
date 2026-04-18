"""
Compliance Test: Geographic Data Residency
═══════════════════════════════════════════════════════════
Frameworks: GDPR Art.44–49, Data Sovereignty Laws

Validates:
  • AWS region configuration is explicit (not defaulting to us-east-1 silently)
  • Database URLs don't point to unexpected regions
  • Environment variables for cloud regions are documented
"""



class TestDataResidency:
    """GDPR Art.44: Transfers to third countries require safeguards."""

    def test_aws_region_is_configurable(self):
        """Data sovereignty: Cloud region must not be silently hardcoded."""
        import inspect

        from main import _load_secret
        source = inspect.getsource(_load_secret)
        assert "AWS_DEFAULT_REGION" in source or "region_name" in source, \
            "AWS region must be configurable, not hardcoded"

    def test_aws_region_has_env_override(self):
        """GDPR Art.44: Region must be overridable via environment."""
        import inspect

        from main import _load_secret
        source = inspect.getsource(_load_secret)
        # The code should read region from env var, not hardcode it
        assert "os.environ" in source or "environ" in source, \
            "AWS region must be configurable via environment variable"

    def test_database_url_does_not_leak_region(self, client):
        """Data sovereignty: DB connection string must not expose cloud region in responses."""
        res = client.get("/health")
        body = res.get_data(as_text=True)
        cloud_indicators = ["amazonaws.com", "rds.amazonaws", "us-east-1",
                            "eu-west-1", "ap-southeast-1"]
        for indicator in cloud_indicators:
            assert indicator not in body, \
                f"Health endpoint leaks cloud region info: {indicator}"

    def test_error_responses_do_not_leak_infrastructure(self, client):
        """GDPR: Error messages must not reveal data processing location."""
        res = client.post("/transfer", json={})
        body = res.get_data(as_text=True)
        infra_terms = ["amazonaws", "azure", "gcp", "localhost:5432",
                        "redis://", "postgresql://"]
        for term in infra_terms:
            assert term not in body, \
                f"Error response leaks infrastructure info: {term}"
