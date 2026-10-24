import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import vm from "node:vm";
import { loadScript } from "./qml-script.mjs";

const store = loadScript(new URL("../Common/settings/SettingsStore.js", import.meta.url));

test("legacy insets migrate to independent sides that can reset without changing the other end", () => {
    const migrated = store.migrateToVersion({
        configVersion: 42,
        barInsetPaddingShared: 20,
        barConfigs: [{ id: "legacy", barInsetPadding: 20 }, { id: "zero", barInsetPadding: 0 },
            { id: "separate", barInsetPadding: 16, barInsetPaddingStart: 0, barInsetPaddingEnd: 48 }]
    }, 43);
    const plain = JSON.parse(JSON.stringify(migrated));
    assert.deepEqual(plain.barConfigs, [
        { id: "legacy", barInsetPaddingStart: 20, barInsetPaddingEnd: 20 },
        { id: "zero", barInsetPaddingStart: 0, barInsetPaddingEnd: 0 },
        { id: "separate", barInsetPaddingStart: 0, barInsetPaddingEnd: 48 }
    ]);
    assert.equal(plain.barInsetPaddingStartShared, 20);
    assert.equal(plain.barInsetPaddingEndShared, 20);
    assert.equal("barInsetPaddingShared" in plain, false);
});

test("bar ends resolve independently and resetting a side preserves the other in local and synced modes", () => {
    const source = readFileSync(new URL("../Common/SettingsData.qml", import.meta.url), "utf8");
    const method = source.match(/^    function barInsetPaddingFor\([^]*?^    }/m);
    assert.ok(method, "SettingsData exposes bar inset resolution");
    const settings = vm.createContext({
        barInsetPaddingSyncAll: false,
        barInsetPaddingStartShared: -1,
        barInsetPaddingEndShared: -1
    });
    vm.runInContext(method[0], settings);
    const resolve = (config, auto = 4) => [settings.barInsetPaddingFor(config, false, auto), settings.barInsetPaddingFor(config, true, auto)];
    const config = { barInsetPaddingStart: 0, barInsetPaddingEnd: 48 };
    assert.deepEqual(resolve(config), [0, 48]);
    config.barInsetPaddingStart = -1;
    assert.deepEqual(resolve(config), [4, 48]);
    assert.deepEqual(resolve({ barInsetPaddingStart: -1, barInsetPaddingEnd: 0 }), [4, 0]);
    assert.deepEqual(resolve({ barInsetPaddingStart: null, barInsetPaddingEnd: 20 }, 8), [8, 20]);

    settings.barInsetPaddingSyncAll = true;
    assert.deepEqual(resolve(config), [4, 4]);
    settings.barInsetPaddingStartShared = 0;
    settings.barInsetPaddingEndShared = 32;
    assert.deepEqual(resolve(config), [0, 32]);
    settings.barInsetPaddingEndShared = -1;
    assert.deepEqual(resolve(config, 8), [0, 8]);
    settings.barInsetPaddingSyncAll = false;
    assert.deepEqual(resolve(config), [4, 48]);
});
