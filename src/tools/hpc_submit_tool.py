"""
HPC Job Submission Tool
Submits SLURM jobs to Harvey via SSH.

Week 3 implementation.
"""

# TODO Week 3: paramiko SSH + sbatch

def submit_job(host: str, user: str, key_path: str, sbatch_script: str) -> str:
    """SSH into Harvey and submit a SLURM job. Returns job_id."""
    raise NotImplementedError("Week 3: implement SLURM submission via paramiko")


def poll_job(host: str, user: str, key_path: str, job_id: str) -> str:
    """Check SLURM job status. Returns: RUNNING | COMPLETED | FAILED"""
    raise NotImplementedError("Week 3: implement squeue polling")


def pull_results(host: str, user: str, key_path: str, remote_dir: str, local_dir: str) -> None:
    """rsync result files from Harvey to local."""
    raise NotImplementedError("Week 3: implement rsync result pull")
