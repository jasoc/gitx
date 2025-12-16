import { ChangeDetectionStrategy, Component, input } from '@angular/core';

@Component({
  selector: 'app-terminal',
  templateUrl: './terminal.component.html',
  styleUrl: './terminal.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class TerminalComponent {
  title = input<string>('');
  code = input<string>('');
  ariaLabel = input<string>('');
}
