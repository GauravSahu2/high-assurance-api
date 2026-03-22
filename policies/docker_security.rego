# OPA policy: Dockerfile security requirements
package docker.security

import rego.v1

# Must not run as root
deny contains msg if {
    input.stages[_].instructions[_].cmd == "USER"
    input.stages[_].instructions[_].value == "root"
    msg := "Container must not run as root user"
}

# Must have HEALTHCHECK
deny contains msg if {
    stage := input.stages[_]
    not any_healthcheck(stage)
    msg := "Dockerfile must include a HEALTHCHECK instruction"
}

any_healthcheck(stage) if {
    stage.instructions[_].cmd == "HEALTHCHECK"
}
