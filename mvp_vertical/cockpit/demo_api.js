/*
 * Demo API Adapter
 * Static fixture layer only. No runtime, no writes.
 */

window.PANTHEON_DEMO_API = {
  enabled: true,
  hermes: {
    enabledByDefault: false,
    userToggle: true
  }
};

export function demoProject(projects, id) {
  return projects.find(project => project.project_id === id || project.code === id);
}
