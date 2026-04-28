#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "covdb_user.h"

typedef struct {
    char* signal;
    char* range;
    int line;
    int width;
    int covered;
    int coverable;
} TglVpEntry;

typedef struct {
    char* full_name;
    char* rtl_file;
    TglVpEntry* vps;
    int vp_count;
    int vp_capacity;
} ModuleEntry;

typedef struct {
    ModuleEntry* items;
    int count;
    int capacity;
} ModuleList;

static const char* obj_type_name(covdbHandle obj, covdbHandle region) {
    covdbObjTypesT objType = covdb_get(obj, region, NULL, covdbType);
    switch (objType) {
        case covdbContainer: return "covdbContainer";
        default: return "other";
    }
}

static void module_list_init(ModuleList* list) {
    list->items = NULL;
    list->count = 0;
    list->capacity = 0;
}

static void module_list_free(ModuleList* list) {
    int i;
    int j;
    if (list == NULL) return;
    for (i = 0; i < list->count; i++) {
        free(list->items[i].full_name);
        free(list->items[i].rtl_file);
        for (j = 0; j < list->items[i].vp_count; j++) {
            free(list->items[i].vps[j].signal);
            free(list->items[i].vps[j].range);
        }
        free(list->items[i].vps);
    }
    free(list->items);
    list->items = NULL;
    list->count = 0;
    list->capacity = 0;
}

static ModuleEntry* module_list_get_or_add(ModuleList* list, const char* full_name, const char* rtl_file) {
    int i;
    ModuleEntry* new_items;
    int new_capacity;

    if (list == NULL || full_name == NULL) return NULL;

    for (i = 0; i < list->count; i++) {
        if (strcmp(list->items[i].full_name, full_name) == 0) {
            if ((list->items[i].rtl_file == NULL || list->items[i].rtl_file[0] == '\0') &&
                rtl_file != NULL && rtl_file[0] != '\0') {
                list->items[i].rtl_file = strdup(rtl_file);
            }
            return &list->items[i];
        }
    }

    if (list->count == list->capacity) {
        new_capacity = list->capacity == 0 ? 64 : list->capacity * 2;
        new_items = (ModuleEntry*)realloc(list->items, sizeof(ModuleEntry) * (size_t)new_capacity);
        if (new_items == NULL) return NULL;
        list->items = new_items;
        list->capacity = new_capacity;
    }

    list->items[list->count].full_name = strdup(full_name);
    list->items[list->count].rtl_file = NULL;
    list->items[list->count].vps = NULL;
    list->items[list->count].vp_count = 0;
    list->items[list->count].vp_capacity = 0;
    if (list->items[list->count].full_name == NULL) return NULL;

    if (rtl_file != NULL && rtl_file[0] != '\0') {
        list->items[list->count].rtl_file = strdup(rtl_file);
        if (list->items[list->count].rtl_file == NULL) {
            free(list->items[list->count].full_name);
            list->items[list->count].full_name = NULL;
            return NULL;
        }
    }

    list->count++;
    return &list->items[list->count - 1];
}

static int module_entry_add_tgl_vp(ModuleEntry* entry,
                                   const char* signal,
                                   int line,
                                   int width,
                                   int covered,
                                   int coverable) {
    int i;
    TglVpEntry* new_vps;
    int new_capacity;
    char range_text[32];

    if (entry == NULL || signal == NULL || signal[0] == '\0') return 0;

    snprintf(range_text, sizeof(range_text), "%d-%d", line > 0 ? line : 0, line > 0 ? line : 0);

    for (i = 0; i < entry->vp_count; i++) {
        if (entry->vps[i].line == line && strcmp(entry->vps[i].signal, signal) == 0) {
            entry->vps[i].width = width;
            entry->vps[i].covered = covered;
            entry->vps[i].coverable = coverable;
            return 1;
        }
    }

    if (entry->vp_count == entry->vp_capacity) {
        new_capacity = entry->vp_capacity == 0 ? 16 : entry->vp_capacity * 2;
        new_vps = (TglVpEntry*)realloc(entry->vps, sizeof(TglVpEntry) * (size_t)new_capacity);
        if (new_vps == NULL) return 0;
        entry->vps = new_vps;
        entry->vp_capacity = new_capacity;
    }

    entry->vps[entry->vp_count].signal = strdup(signal);
    entry->vps[entry->vp_count].range = strdup(range_text);
    if (entry->vps[entry->vp_count].signal == NULL || entry->vps[entry->vp_count].range == NULL) return 0;
    entry->vps[entry->vp_count].line = line;
    entry->vps[entry->vp_count].width = width;
    entry->vps[entry->vp_count].covered = covered;
    entry->vps[entry->vp_count].coverable = coverable;
    entry->vp_count++;
    return 1;
}

static covdbHandle find_metric(covdbHandle test, const char* metricName) {
    covdbHandle iter = covdb_iterate(test, covdbMetrics);
    covdbHandle metric;
    if (iter == NULL) return NULL;

    metric = covdb_scan(iter);
    while (metric != NULL) {
        char* name = covdb_get_str(metric, covdbFullName);
        if (name != NULL && strcmp(name, metricName) == 0) {
            return metric;
        }
        metric = covdb_scan(iter);
    }
    return NULL;
}

static void collect_tgl_vps_at_level(covdbHandle obj,
                                     covdbHandle region,
                                     covdbHandle test,
                                     int level,
                                     ModuleEntry* entry) {
    covdbHandle childIter;
    covdbHandle child;
    char* name;
    int lineNo;
    int width;
    int covered;
    int coverable;

    if (obj == NULL || entry == NULL) return;
    if (strcmp(obj_type_name(obj, region), "covdbContainer") != 0) return;

    name = covdb_get_str(obj, covdbFullName);
    lineNo = covdb_get(obj, region, test, covdbLineNo);
    width = covdb_get(obj, region, NULL, covdbWidth);
    covered = covdb_get(obj, region, test, covdbCovered);
    coverable = covdb_get(obj, region, NULL, covdbCoverable);

    if (!(level == 0 && name != NULL && (strcmp(name, "port") == 0 || strcmp(name, "signal") == 0))) {
        if ((level == 1 || (level == 0 && lineNo > 0)) && name != NULL && name[0] != '\0' && coverable > 0) {
            if (!module_entry_add_tgl_vp(entry, name, lineNo, width, covered, coverable)) {
                return;
            }
        }
    }

    if (level == 0) {
        childIter = covdb_iterate(obj, covdbObjects);
        if (childIter == NULL) return;
        child = covdb_scan(childIter);
        while (child != NULL) {
            collect_tgl_vps_at_level(child, region, test, level + 1, entry);
            child = covdb_scan(childIter);
        }
        covdb_release_handle(childIter);
    }
}

static void collect_tgl_vps_for_instance(covdbHandle qualifiedInstance,
                                         covdbHandle test,
                                         const char* instanceName,
                                         const char* rtlFile,
                                         ModuleList* modules) {
    covdbHandle rootIter = covdb_iterate(qualifiedInstance, covdbObjects);
    covdbHandle rootObj;
    ModuleEntry* entry;

    if (rootIter == NULL || instanceName == NULL || modules == NULL) return;

    entry = module_list_get_or_add(modules, instanceName, rtlFile);
    if (entry == NULL) return;

    rootObj = covdb_scan(rootIter);
    while (rootObj != NULL) {
        collect_tgl_vps_at_level(rootObj, qualifiedInstance, test, 0, entry);
        rootObj = covdb_scan(rootIter);
    }
}

static void process_definition_instances(covdbHandle definition,
                                         covdbHandle metric,
                                         covdbHandle test,
                                         int firstOnly,
                                         ModuleList* modules) {
    covdbHandle iter = covdb_iterate(definition, covdbInstances);
    covdbHandle instance;

    if (iter == NULL) return;

    instance = covdb_scan(iter);
    while (instance != NULL) {
        covdbHandle qualifiedInstance = covdb_get_qualified_handle(instance, metric, covdbIdentity);
        char* instanceName = covdb_get_str(instance, covdbFullName);
        char* rtlFile = covdb_get_str(instance, covdbFileName);
        if (qualifiedInstance != NULL && instanceName != NULL) {
            collect_tgl_vps_for_instance(qualifiedInstance, test, instanceName, rtlFile, modules);
        }
        if (firstOnly) break;
        instance = covdb_scan(iter);
    }
}

static void json_escape_print(const char* text) {
    const unsigned char* p = (const unsigned char*)text;
    if (text == NULL) {
        printf("\"\"");
        return;
    }

    putchar('"');
    while (*p != '\0') {
        if (*p == '\\' || *p == '"') {
            putchar('\\');
            putchar((char)*p);
        } else if (*p == '\n') {
            printf("\\n");
        } else if (*p == '\r') {
            printf("\\r");
        } else if (*p == '\t') {
            printf("\\t");
        } else if (*p < 0x20) {
            printf("\\u%04x", (unsigned int)*p);
        } else {
            putchar((char)*p);
        }
        p++;
    }
    putchar('"');
}

static void print_json_output(const ModuleList* modules, int firstOnly, const char* moduleFilter) {
    int i;
    int j;

    printf("{\n");
    printf("  \"version\": \"UCAPI_TGL\",\n");
    printf("  \"filters\": {\n");
    printf("    \"instance_mode\": ");
    json_escape_print(firstOnly ? "first" : "all");
    if (moduleFilter != NULL) {
        printf(",\n    \"module_filter\": ");
        json_escape_print(moduleFilter);
        printf("\n");
    } else {
        printf("\n");
    }
    printf("  },\n");
    printf("  \"modules\": [\n");

    for (i = 0; i < modules->count; i++) {
        printf("    {\n");
        printf("      \"full_name\": ");
        json_escape_print(modules->items[i].full_name);
        printf(",\n");
        printf("      \"rtl_file\": ");
        json_escape_print(modules->items[i].rtl_file != NULL ? modules->items[i].rtl_file : "");
        printf(",\n");
        printf("      \"vps\": [\n");
        for (j = 0; j < modules->items[i].vp_count; j++) {
            double pct = 0.0;
            if (modules->items[i].vps[j].coverable > 0) {
                pct = ((double)modules->items[i].vps[j].covered * 100.0) /
                      (double)modules->items[i].vps[j].coverable;
            }
            printf("        {\"kind\": \"tgl\", \"range\": ");
            json_escape_print(modules->items[i].vps[j].range);
            printf(", \"signal\": ");
            json_escape_print(modules->items[i].vps[j].signal);
            printf(", \"line\": %d, \"width\": %d, \"covered\": %d, \"coverable\": %d, \"pct\": %.2f}",
                   modules->items[i].vps[j].line,
                   modules->items[i].vps[j].width,
                   modules->items[i].vps[j].covered,
                   modules->items[i].vps[j].coverable,
                   pct);
            if (j + 1 < modules->items[i].vp_count) printf(",");
            printf("\n");
        }
        printf("      ]\n");
        printf("    }");
        if (i + 1 < modules->count) printf(",");
        printf("\n");
    }

    printf("  ]\n");
    printf("}\n");
}

int main(int argc, char* argv[]) {
    covdbHandle design;
    covdbHandle test;
    covdbHandle metric;
    covdbHandle defIter;
    covdbHandle definition;
    const char* mode;
    const char* moduleFilter = NULL;
    int firstOnly;
    ModuleList modules;

    if (argc < 4 || argc > 5) {
        fprintf(stderr, "usage: %s <vdb> <test> <first|all> [module-filter]\n", argv[0]);
        return 1;
    }

    mode = argv[3];
    if (strcmp(mode, "first") == 0) {
        firstOnly = 1;
    } else if (strcmp(mode, "all") == 0) {
        firstOnly = 0;
    } else {
        fprintf(stderr, "mode must be 'first' or 'all'\n");
        return 1;
    }

    if (argc == 5) moduleFilter = argv[4];

    design = covdb_load(covdbDesign, NULL, argv[1]);
    if (design == NULL) {
        fprintf(stderr, "failed to load design: %s\n", argv[1]);
        return 2;
    }
    sleep(1);

    test = covdb_load(covdbTest, design, argv[2]);
    if (test == NULL) {
        fprintf(stderr, "failed to load test: %s\n", argv[2]);
        covdb_unload(design);
        return 3;
    }
    sleep(1);

    metric = find_metric(test, "Tgl");
    if (metric == NULL) {
        fprintf(stderr, "failed to find metric: Tgl\n");
        covdb_unload(test);
        covdb_unload(design);
        return 4;
    }

    module_list_init(&modules);
    defIter = covdb_iterate(design, covdbDefinitions);
    if (defIter == NULL) {
        fprintf(stderr, "failed to iterate definitions\n");
        covdb_unload(test);
        covdb_unload(design);
        return 5;
    }

    definition = covdb_scan(defIter);
    while (definition != NULL) {
        char* definitionName = covdb_get_str(definition, covdbFullName);
        if (definitionName != NULL) {
            if (moduleFilter == NULL || strcmp(definitionName, moduleFilter) == 0) {
                process_definition_instances(definition, metric, test, firstOnly, &modules);
            }
        }
        definition = covdb_scan(defIter);
    }

    print_json_output(&modules, firstOnly, moduleFilter);
    module_list_free(&modules);
    covdb_unload(test);
    covdb_unload(design);
    return 0;
}
