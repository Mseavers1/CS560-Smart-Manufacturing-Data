RESOLVED as of Apr 20 2026

Key Limitation

Your Swarm task can see i2c-1 but the kernel refuses open() with EPERM (Operation not permitted).
That means this is a device permission/cgroup policy denial, not a missing file or bad IMU code.
Why this happens

Linux device files are controlled by both file mode and device-cgroup rules.
In your Swarm environment, bind-mounting i2c-1 alone does not grant usable device access to the task sandbox.
Your Docker version also lacks practical Swarm-side device controls (stack rejected device_cgroup_rules, and service create does not expose --device), so you can’t fully authorize I2C from the stack spec.
How it blocks your implementation

Swarm can deploy/restart containers, but the IMU process cannot open the bus, so sampling never starts.
Result: orchestration works, hardware I/O fails at runtime.
That is why dashboard/Swarm “start all IMUs” is blocked right now: control plane is fine, hardware data plane is denied.
Bottom line

Current blocker is Swarm runtime device authorization for i2c-1 on your node, not your app logic.
