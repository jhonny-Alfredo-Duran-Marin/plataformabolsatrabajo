import { ComponentFixture, TestBed } from '@angular/core/testing';
import { RegistroEgresado } from './registro-egresado';

describe('RegistroEgresado', () => {
  let component: RegistroEgresado;
  let fixture: ComponentFixture<RegistroEgresado>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [RegistroEgresado],
    }).compileComponents();

    fixture = TestBed.createComponent(RegistroEgresado);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
