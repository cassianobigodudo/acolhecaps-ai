#!/usr/bin/env python3
"""
Script de validação do pipeline de CI/CD - Card 8

Este script simula a execução do pipeline localmente,
permitindo validação antes de fazer push para GitHub.
"""

import subprocess
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

class PipelineValidator:
    """Validador de pipeline com análise de logs."""
    
    def __init__(self):
        self.results: Dict[str, Dict] = {}
        self.start_time = datetime.now()
        self.project_root = Path(__file__).parent.parent
        
    def log_step(self, stage: str, status: str, details: str = "") -> None:
        """Registra resultado de uma etapa."""
        print(f"\n{'='*60}")
        print(f"[{stage.upper()}] {status}")
        if details:
            print(f"Details: {details}")
        print('='*60)
        
    def run_command(self, cmd: List[str], description: str) -> Tuple[int, str, str]:
        """Executa comando e captura output."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Timeout executando comando"
        except Exception as e:
            return -1, "", str(e)
    
    def validate_lint(self) -> bool:
        """Valida linting."""
        self.log_step("lint", "INICIANDO")
        
        lint_results = {
            "black": None,
            "isort": None,
            "flake8": None,
            "pylint": None
        }
        
        # Black check
        print("\n→ Verificando Black formatter...")
        rc, stdout, stderr = self.run_command(
            ["black", "--check", "app/", "tests/", "--line-length", "100"],
            "Black check"
        )
        lint_results["black"] = rc == 0
        print(f"  Black: {'✓ PASS' if lint_results['black'] else '⚠ WARN (não bloqueante)'}")
        
        # isort check
        print("\n→ Verificando isort imports...")
        rc, stdout, stderr = self.run_command(
            ["isort", "--check-only", "app/", "tests/", "--profile", "black"],
            "isort check"
        )
        lint_results["isort"] = rc == 0
        print(f"  isort: {'✓ PASS' if lint_results['isort'] else '⚠ WARN (não bloqueante)'}")
        
        # flake8 check
        print("\n→ Verificando flake8...")
        rc, stdout, stderr = self.run_command(
            ["flake8", "app/", "tests/", "--max-line-length=100"],
            "flake8 check"
        )
        lint_results["flake8"] = rc == 0
        if rc == 0:
            print("  flake8: ✓ PASS (sem violações)")
        else:
            print(f"  flake8: Issues encontradas\n{stdout}")
        
        # pylint check (menos strict)
        print("\n→ Verificando pylint...")
        rc, stdout, stderr = self.run_command(
            ["pylint", "app/", "--max-line-length=100", "--disable=C0111,C0103"],
            "pylint check"
        )
        lint_results["pylint"] = rc == 0 or rc < 10  # pylint usa exit codes diferentes
        print(f"  pylint: {'✓ PASS' if lint_results['pylint'] else '⚠ WARN (não bloqueante)'}")
        
        self.results["lint"] = lint_results
        return True  # Lint não bloqueia o pipeline
    
    def validate_tests(self) -> bool:
        """Valida testes."""
        self.log_step("test", "INICIANDO")
        
        test_results = {
            "unit_tests": None,
            "integration_tests": None,
            "coverage": None
        }
        
        # Unit tests
        print("\n→ Executando testes unitários...")
        rc, stdout, stderr = self.run_command(
            ["pytest", "tests/unit/", "-v", "--tb=short", "-x"],
            "Unit tests"
        )
        test_results["unit_tests"] = rc == 0
        
        # Extrair contagem
        if "passed" in stdout:
            import re
            match = re.search(r"(\d+) passed", stdout)
            if match:
                print(f"  Unit tests: ✓ {match.group(1)} testes passaram")
        
        # Integration tests
        print("\n→ Executando testes de integração...")
        rc, stdout, stderr = self.run_command(
            ["pytest", "tests/integration/", "-v", "--tb=short", "-x"],
            "Integration tests"
        )
        test_results["integration_tests"] = rc == 0
        
        if "passed" in stdout:
            import re
            match = re.search(r"(\d+) passed", stdout)
            if match:
                print(f"  Integration tests: ✓ {match.group(1)} testes passaram")
        
        # Coverage
        print("\n→ Gerando relatório de cobertura...")
        rc, stdout, stderr = self.run_command(
            ["pytest", "tests/", "--cov=app", "--cov-report=term", "-q"],
            "Coverage"
        )
        test_results["coverage"] = rc == 0
        if "%" in stdout:
            print(f"  Coverage: {[line for line in stdout.split('\n') if '%' in line][-1]}")
        
        self.results["test"] = test_results
        return all(test_results.values())
    
    def validate_security(self) -> bool:
        """Valida segurança."""
        self.log_step("security", "INICIANDO")
        
        security_results = {
            "bandit": None,
            "safety": None
        }
        
        # Bandit
        print("\n→ Executando Bandit scan...")
        rc, stdout, stderr = self.run_command(
            ["bandit", "-r", "app/", "-ll"],  # -ll para Low/Medium severity
            "Bandit"
        )
        security_results["bandit"] = rc == 0
        if rc == 0:
            print("  Bandit: ✓ Sem vulnerabilidades encontradas")
        else:
            print(f"  Bandit: ⚠ Issues encontradas (não bloqueante)")
        
        # Safety
        print("\n→ Verificando dependências com Safety...")
        rc, stdout, stderr = self.run_command(
            ["safety", "check", "-q"],
            "Safety"
        )
        security_results["safety"] = rc == 0
        if rc == 0:
            print("  Safety: ✓ Todas as dependências OK")
        else:
            print(f"  Safety: ⚠ Issues encontradas (não bloqueant)")
        
        self.results["security"] = security_results
        return True  # Security não bloqueia o pipeline
    
    def validate_build(self) -> bool:
        """Valida build."""
        self.log_step("build", "INICIANDO")
        
        build_results = {
            "imports": True,
            "syntax": True,
            "env_config": True
        }
        
        # Validar imports
        print("\n→ Validando imports principais...")
        imports_to_test = [
            "from app.services.graph_service import executar_acolhimento",
            "from app.services.rag_service import obter_rag_service",
            "from app.services.mcp_territorial_tool import obter_tool_territorial",
            "from app.services.observability import RequestContext",
            "from app.models.acolhimento import EntradaAcolhimento, FichaTriagemCAPS",
        ]
        
        for imp in imports_to_test:
            rc, stdout, stderr = self.run_command(
                ["python", "-c", imp],
                f"Import: {imp.split()[-1]}"
            )
            if rc != 0:
                build_results["imports"] = False
                print(f"  ✗ {imp}")
            else:
                print(f"  ✓ {imp.split()[-1]}")
        
        # Python syntax check
        print("\n→ Verificando syntax Python...")
        rc, stdout, stderr = self.run_command(
            ["python", "-m", "py_compile", "app/services/graph_service.py"],
            "Syntax check"
        )
        build_results["syntax"] = rc == 0
        print(f"  Syntax: {'✓ OK' if build_results['syntax'] else '✗ ERRO'}")
        
        # .env.example
        print("\n→ Verificando .env.example...")
        build_results["env_config"] = Path(self.project_root / ".env.example").exists()
        print(f"  .env.example: {'✓ Presente' if build_results['env_config'] else '✗ Faltando'}")
        
        self.results["build"] = build_results
        return all(build_results.values())
    
    def generate_report(self) -> None:
        """Gera relatório final."""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        
        self.log_step("report", "GERANDO RELATÓRIO")
        
        print(f"\n📊 RELATÓRIO DO PIPELINE\n")
        print(f"Tempo Total: {elapsed:.1f}s\n")
        
        for stage, results in self.results.items():
            if isinstance(results, dict):
                status = "✓ PASS" if all(v for v in results.values() if isinstance(v, bool)) else "⚠ WARN"
                print(f"{stage.upper()}: {status}")
                for key, value in results.items():
                    if isinstance(value, bool):
                        symbol = "✓" if value else "✗"
                        print(f"  {symbol} {key}")
        
        print("\n" + "="*60)
        print("✅ PIPELINE VALIDATION COMPLETED")
        print("="*60)
        
        # JSON output
        report = {
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": elapsed,
            "results": self.results
        }
        
        report_file = self.project_root / "pipeline-report.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📝 Relatório salvo: {report_file}")
    
    def run_all(self) -> int:
        """Executa todas as validações."""
        print("\n" + "="*60)
        print("VALIDAÇÃO DO PIPELINE DE CI/CD")
        print("="*60)
        
        try:
            self.validate_lint()
            if not self.validate_tests():
                print("\n❌ Testes falharam!")
                return 1
            self.validate_security()
            if not self.validate_build():
                print("\n❌ Build validation falhou!")
                return 1
            self.generate_report()
            return 0
        except KeyboardInterrupt:
            print("\n\n⚠️ Validação interrompida pelo usuário")
            return 130
        except Exception as e:
            print(f"\n❌ Erro durante validação: {e}")
            return 1

def main():
    """Entry point."""
    validator = PipelineValidator()
    sys.exit(validator.run_all())

if __name__ == "__main__":
    main()
