import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { TerminalComponent } from '../components/terminal/terminal.component';

@Component({
  selector: 'app-root',
  templateUrl: './app.html',
  styleUrl: './app.scss',
  imports: [RouterOutlet, TerminalComponent],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class App {
  protected readonly installScript = 'curl -sfL https://gitx.parisius.dev | sh -';

  protected readonly quickCheckScript = 'gitx --help';

  protected readonly workflowScript = `# 1. Clone once and create a workspace for the default branch
gitx clone jasoc/gitx

# 2. Create a dedicated worktree for a feature branch
gitx branch add jasoc/gitx feature/my-work

# 3. Jump into the worktree for that branch (fish)
cd (gitx go jasoc/gitx -b feature/my-work)

# 4. Or open your editor directly on that branch
gitx code jasoc/gitx --branch feature/my-work

# 5. Next time you open your workspace, gitx restores the last-opened branch
cd (gitx go jasoc/gitx)  # jumps to feature/my-work`;
}
