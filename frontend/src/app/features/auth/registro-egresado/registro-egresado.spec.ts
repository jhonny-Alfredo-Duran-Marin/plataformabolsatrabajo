import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { RegistroEgresado } from './registro-egresado';

describe('RegistroEgresado', () => {
  let component: RegistroEgresado;
  let fixture: ComponentFixture<RegistroEgresado>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [RegistroEgresado],
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(RegistroEgresado);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
