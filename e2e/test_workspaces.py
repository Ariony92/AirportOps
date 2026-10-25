import os
from playwright.sync_api import sync_playwright, expect

BASE = os.getenv('AIRPORTOPS_E2E_URL', 'http://127.0.0.1:5173')


def test_navigation_and_live_playback():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 900})
        page.goto(BASE, wait_until='networkidle')
        expect(page.get_by_role('heading', name='Simulation opérationnelle')).to_be_visible()
        expect(page.get_by_role('img', name='Plan animé des cinq portes, appareils et véhicules affectés aux opérations')).to_be_visible()
        expect(page.get_by_text('Vols planifiés')).to_be_visible()
        page.get_by_role('button', name='Démarrer').click()
        expect(page.get_by_role('button', name='Pause')).to_be_visible()
        page.get_by_role('button', name='Pause').click()
        expect(page.get_by_role('button', name='Démarrer')).to_be_visible()
        page.locator('input[aria-label="Position dans la simulation"]').focus()
        page.keyboard.press('ArrowRight')
        expect(page.get_by_text('Journal des événements')).to_be_visible()
        page.get_by_role('link', name='Vols & flotte').click()
        expect(page.get_by_role('heading', name='Vols et flotte aérienne')).to_be_visible()
        page.get_by_role('link', name='Infrastructures').click()
        expect(page.get_by_role('heading', name='Pistes et services au sol')).to_be_visible()
        page.get_by_role('link', name='Incidents & KPI').click()
        expect(page.get_by_role('heading', name='Incidents et optimisation')).to_be_visible()
        page.get_by_role('link', name='Scénarios').click()
        expect(page.get_by_role('heading', name='Scénarios enregistrés')).to_be_visible()
        browser.close()


def test_scenario_is_calculated_by_api():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(BASE+'/#/scenarios', wait_until='networkidle')
        expect(page.get_by_role('heading', name='Scénarios enregistrés')).to_be_visible()
        page.get_by_label('Nom du scénario').fill('Test navigateur')
        page.get_by_role('button', name='Créer').click()
        expect(page.get_by_role('heading', name='Test navigateur')).to_be_visible()
        scenario = page.locator('.scenario-item').filter(has=page.get_by_role('heading', name='Test navigateur'))
        scenario.get_by_role('button', name='Calculer').click()
        expect(page.get_by_text('Prévision calculée et enregistrée par le backend.')).to_be_visible()
        expect(scenario.get_by_text('vols terminés')).to_be_visible()
        page.once('dialog', lambda dialog: dialog.accept())
        scenario.get_by_role('button',name='Supprimer Test navigateur').click()
        browser.close()
