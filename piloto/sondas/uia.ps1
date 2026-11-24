# Sonda: a UIA (UI Automation) numa janela — RESOLVE 19.1.4 a expoe (botoes, menus, campos, estado); o MC NAO
# (o qwindows.dll dele veio sem o provedor). Medido 2026-11-04. ASCII de proposito (PowerShell 5.1 sem BOM).
#   powershell -File uia.ps1 arvore <hwnd>
#   powershell -File uia.ps1 invocar <hwnd> "New Project"
#   powershell -File uia.ps1 valor <hwnd> "<nome do campo>" "<texto>"
# Atencao: a acao pela UIA traz o app a FRENTE. Nomes com reticencias: compare pelo comeco.
param([string]$acao, [int]$hwnd, [string]$nome, [string]$valor)
Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes
$A = [System.Windows.Automation.AutomationElement]
$raiz = if ($hwnd) { $A::FromHandle([IntPtr]$hwnd) } else { $A::RootElement }
function Achar($r, $n) {
  $c = New-Object System.Windows.Automation.PropertyCondition($A::NameProperty, $n)
  return $r.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $c)
}
$t0 = Get-Date
switch ($acao) {
  'invocar' { $e = Achar $raiz $nome; if (-not $e) { "NAO ACHEI '$nome'"; exit 1 }
              $p = $e.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern); $p.Invoke(); "invocado '$nome' em $(((Get-Date)-$t0).TotalMilliseconds) ms" }
  'valor'   { $e = Achar $raiz $nome; if (-not $e) { "NAO ACHEI '$nome'"; exit 1 }
              $p = $e.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern); $p.SetValue($valor); "valor posto em '$nome': $($p.Current.Value)" }
  'arvore'  { $w = [System.Windows.Automation.TreeWalker]::ControlViewWalker
              function V($el,$p){ if($p -gt 14){return}; $c=$w.GetFirstChild($el); while($c){ $i=$c.Current; if($i.Name -or $i.ControlType.ProgrammaticName -match 'Edit|Button|Tab|List|Menu|Combo|CheckBox|Text'){ "{0}{1} | {2} | '{3}' | {4}" -f ('  '*$p),$i.ControlType.ProgrammaticName,$i.ClassName,$i.Name,$i.BoundingRectangle }; V $c ($p+1); $c=$w.GetNextSibling($c)} }
              V $raiz 0 }
}
