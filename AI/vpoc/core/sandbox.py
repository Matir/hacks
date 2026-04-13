import logging
import typing
import docker
import docker.errors
from pathlib import Path
from core.models import ServerConfig

logger = logging.getLogger(__name__)

class SandboxError(Exception):
    """Raised when sandbox execution fails."""
    pass

class SandboxResult(typing.NamedTuple):
    """Results from a sandbox execution."""
    exit_code: int
    stdout: str
    stderr: str
    duration: float  # seconds
    cpu_peak: float  # percentage
    mem_peak: int    # bytes

class SandboxRunner:
    """Manages hardened Docker sandboxes for PoC validation.
    
    Enforces gVisor isolation, no-egress networking, privilege reduction,
    and strict resource limits.
    """

    def __init__(self, config: ServerConfig) -> None:
        self.config = config
        self._client = docker.from_env()
        self._runtime = config.runtime if config.require_gvisor else "runc"

    def check_gvisor(self) -> bool:
        """Checks if the configured gVisor runtime is available."""
        try:
            info = self._client.info()
            runtimes = info.get("Runtimes", {})
            return self.config.runtime in runtimes
        except Exception as e:
            logger.error("Failed to check Docker runtimes: %s", e)
            return False

    async def run_poc(
        self,
        image_id: str,
        command: typing.Optional[str] = None,
        volumes: typing.Optional[typing.Dict[str, typing.Dict[str, str]]] = None,
        timeout: int = 300,
    ) -> SandboxResult:
        """
        Executes a PoC container with full hardening.
        
        :param image_id: Docker image to run.
        :param command: Optional command override.
        :param volumes: Optional host volumes to mount.
        :param timeout: Maximum execution time in seconds.
        """
        container = None
        try:
            # Prepare security options
            security_opt = ["no-new-privileges"]
            
            # Start the container
            container = self._client.containers.run(
                image=image_id,
                command=command,
                runtime=self._runtime,
                network_mode="none",
                cap_drop=["ALL"],
                security_opt=security_opt,
                mem_limit=self.config.default_memory_limit,
                nano_cpus=int(self.config.default_cpu_limit * 1e9),
                pids_limit=100,  # Prevent fork bombs
                read_only=True,
                tmpfs={
                    "/tmp": "exec",
                    "/var/tmp": "exec",
                },
                volumes=volumes or {},
                detach=True,
                stderr=True,
                stdout=True,
            )

            # Wait for completion with timeout
            import asyncio
            import time
            start_time = time.time()
            
            # Simple polling wait for MVP
            exit_code = -1
            while time.time() - start_time < timeout:
                container.reload()
                if container.status == "exited":
                    result = container.wait()
                    exit_code = result.get("StatusCode", -1)
                    break
                await asyncio.sleep(1)
            else:
                # Timeout reached
                container.kill()
                exit_code = 124  # Standard timeout exit code
                logger.warning("PoC container %s timed out after %ds", container.id, timeout)

            duration = time.time() - start_time
            stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="ignore")
            stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="ignore")

            # TODO: Implement actual resource peak monitoring via container.stats()
            
            return SandboxResult(
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                duration=duration,
                cpu_peak=0.0,
                mem_peak=0,
            )

        except docker.errors.ImageNotFound:
            raise SandboxError(f"Image {image_id} not found.")
        except Exception as e:
            logger.exception("Error during sandbox execution: %s", e)
            raise SandboxError(f"Sandbox execution failed: {str(e)}")
        finally:
            if container:
                try:
                    container.remove(force=True)
                except Exception:
                    pass
