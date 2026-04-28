#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <stdarg.h>
#include <ctype.h>
#include "covdb_user.h"
#include <unistd.h>


// env:export CODE_BASE_PATH=/home/c910/wangyahao/openc910/C910_RTL_FACTORY && \
//     export UCAPI_LIB=/home/yian/Synopsys/vcs/V-2023.12-SP2/linux64/lib && \
//     export LD_LIBRARY_PATH=/home/yian/Synopsys/vcs/V-2023.12-SP2/linux64/lib:$LD_LIBRARY_PATH

// compile command:
// gcc -I/home/yian/Synopsys/vcs/V-2023.12-SP2/include src/CoverageExtractToolServer.c -L/home/yian/Synopsys/vcs/V-2023.12-SP2/linux64/lib -o genUtil/CoverageExtractToolServer.exe -lucapi

// 服务模式：启动时无需参数，通过 stdin 接收查询命令
// 命令格式：<vdbPath> <testPath> <moduleName> <start-end>
// 示例：/home/c910/wangyahao/openc910/smart_run/tb1/my_forcerv_test /home/c910/wangyahao/openc910/smart_run/tb1/my_forcerv_test.vdb/test1 ct_ifu_l1_refill 0-5000
// 退出命令：exit
// /home/c910/wangyahao/openc910/smart_run/work_force/simv.vdb /home/c910/wangyahao/openc910/smart_run/work_force/simv.vdb/task1_iter_0 ct_ifu_l1_refill 0-5000
typedef struct {
    char* vdbName;
    char* testName;
    char* targetModuleName;
    int startLineNo;
    int endLineNo;
} CoverageParams;

typedef struct {
    int lineNo;
    int coverState;
} CoverStatus;

typedef struct {
    covdbHandle design;
    covdbHandle test;
    covdbHandle lineMetric;
    covdbHandle ConditionMetric;
    covdbHandle TglMetric;
    covdbHandle FsmMetric;
    covdbHandle BranchMetric;

    char currentVdb[512];
    char currentTest[512];
    int initialized;
} CoverageServiceState;

#define MAX_TGL_SIGNALS 4096
#define MAX_FSMS 64
#define MAX_FSM_STATES 128
#define MAX_FSM_TRANSITIONS 256
#define MAX_BRANCH_SPECS 1024
#define MAX_BRANCH_EXPRS 128
#define MAX_BRANCH_CASE_ITEMS 256
#define MAX_DECODE_TEXT 8192
#define MAX_CMD_LEN 2048

typedef struct {
    char name[256];
    int lineNo;
    int width;
    int isVector;
} TglSignalMeta;

typedef struct {
    char name[128];
    int lineNo;
} FsmStateMeta;

typedef struct {
    int fromId;
    int toId;
    int lineNo;
} FsmTransitionMeta;

typedef struct {
    char currentName[256];
    int lineNo;
    int width;
    int stateCount;
    int transitionCount;
    FsmStateMeta states[MAX_FSM_STATES];
    FsmTransitionMeta transitions[MAX_FSM_TRANSITIONS];
} FsmMeta;

typedef struct {
    int index;
    int lineNo;
    char name[256];
} BranchCaseItemMeta;

typedef struct {
    int lineNo;
    int index;
    int parentBit;
    int trueClauseLine;
    int falseClauseLine;
    char expr[512];
} BranchExprMeta;

typedef struct {
    int rootLine;
    int fileId;
    int isCase;
    char rootExpr[512];
    int exprCount;
    int caseItemCount;
    BranchExprMeta exprs[MAX_BRANCH_EXPRS];
    BranchCaseItemMeta caseItems[MAX_BRANCH_CASE_ITEMS];
} BranchSpecMeta;

typedef struct {
    char vdbPath[512];
    char moduleName[256];
    char sourceFile[512];
    int loaded;
    int fileId;
    int tglSignalCount;
    int fsmCount;
    int branchSpecCount;
    TglSignalMeta tglSignals[MAX_TGL_SIGNALS];
    FsmMeta fsms[MAX_FSMS];
    BranchSpecMeta branchSpecs[MAX_BRANCH_SPECS];
} ModuleShapeCache;

typedef struct {
    const char* kindKey;
    const char* displayName;
    int covered;
    int coverable;
    int matchedObjects;
} CoverageMetricSummary;

typedef struct {
    int startLineNo;
    int endLineNo;
    FILE* sourceFile;
    CoverageMetricSummary* summary;
    int* lineStates;
    int lineStateCapacity;
} TraversalContext;

typedef void (*traverseFunction)(covdbHandle obj, covdbHandle regionHandle,
    covdbHandle testHandle, int level, TraversalContext* ctx);

static CoverageServiceState g_state = {0};
static ModuleShapeCache g_moduleShape = {0};
static const BranchSpecMeta* g_branchSpecStack[64] = {0};

char* getHdlType(covdbHandle hdl, covdbHandle regionHdl);
static covdbHandle loadDesign(const char* vdbName);
static void unloadDesign(covdbHandle design);
static covdbHandle loadTest(covdbHandle design, const char* testName);
static void unloadTest(covdbHandle test);
static covdbHandle findTargetDefinition(covdbHandle design, char* targetModuleName);
static covdbHandle findTargetInstance(covdbHandle definition);
static covdbHandle findLineMetric(covdbHandle test);
static covdbHandle findMetric(covdbHandle test,char* metricName);
static int checkCoverage(covdbHandle qualifiedTargetInstance, covdbHandle test, int startLineNo, int endLineNo, int* coveredCount, int* notCoveredCount, CoverStatus* coverStatus);
static covdbHandle getQualifiedTargetInstance(covdbHandle design, covdbHandle Metric, char* targetModuleName);
static void initCache(CoverStatus* cache, int size);
static float getCoverageData(covdbHandle qualifiedTargetInstance,
    covdbHandle test,
    int startLineNo,
    int endLineNo,
    char* output,
    CoverageMetricSummary* summary,
    traverseFunction traverseFunction);
static void getModuleCoverageSummary(covdbHandle qualifiedTargetInstance,
    covdbHandle test,
    CoverageMetricSummary* summary);
static void resetModuleShapeCache(void);
static int prepareModuleShapeCache(const char* vdbName, const char* moduleName, const char* sourceFile);
static int parseTglShapeForModule(const char* vdbName, const char* moduleName, ModuleShapeCache* cache);
static int parseFsmShapeForModule(const char* vdbName, const char* moduleName, ModuleShapeCache* cache);
static int parseBranchShapeForFileId(const char* vdbName, int fileId, ModuleShapeCache* cache);
static int resolveSourceFileId(const char* vdbName, const char* sourceFile);
static FILE* openGzipTextFile(const char* path);
static void closeGzipTextFile(FILE* fp);
static int extractXmlAttrStr(const char* line, const char* attr, char* out, size_t outSize);
static int extractXmlAttrInt(const char* line, const char* attr, int* value);
static void xmlUnescape(const char* input, char* output, size_t outputSize);
static void trimSpaces(char* text);
static void appendText(char* buffer, size_t bufferSize, const char* fmt, ...);
static void sanitizeSummaryValue(const char* input, char* output, size_t outputSize);
static void normalizeBranchVector(const char* input, char* output, size_t outputSize);
static int getVectorBit(const char* vector, int positionFromRight);
static int getVectorBitFromLeft(const char* vector, int positionFromLeft);
static int decodeBranchExprState(const BranchExprMeta* expr, const char* vector);
static int decodeBranchExprStateFromLeft(const BranchExprMeta* expr, const char* vector);
static int decodeBranchVectorWithOrder(const BranchSpecMeta* spec, const char* vector, char* decoded, size_t decodedSize, int fromRight);
static int decodeBranchVector(const BranchSpecMeta* spec, const char* vector, char* decoded, size_t decodedSize);
static const BranchSpecMeta* findBranchSpecMeta(const char* name, int lineNo);
static const BranchSpecMeta* findBranchSpecMetaByChildLine(int lineNo);
static const FsmMeta* findFsmMeta(const char* name, int lineNo);
static const TglSignalMeta* findTglSignalMeta(const char* name, int lineNo);
static const char* findFsmStateName(const FsmMeta* meta, int stateId);
static int isLineWithinRange(int lineNo, const TraversalContext* ctx);
static void recordMetricCoverage(TraversalContext* ctx, int covered, int coverable);
static void recordLineCoverage(TraversalContext* ctx, int lineNo, int covered);
static float getMetricSummaryScore(const CoverageMetricSummary* summary);
static void printVpSummarySection(const char* moduleName,
    int startLineNo,
    int endLineNo,
    const char* qualifiedInstance,
    const char* sourceFile,
    CoverageMetricSummary* summaries,
    int summaryCount);

void printCoverageParams(CoverageParams params);

void traverseLineCoverageObjects(covdbHandle obj, covdbHandle regionHandle,
    covdbHandle testHandle, int level, TraversalContext* ctx);
    
void traverseConditionCoverageObjects(covdbHandle obj, covdbHandle regionHandle,
    covdbHandle testHandle, int level, TraversalContext* ctx);

void traverseTglCoverageObjects(covdbHandle obj, covdbHandle regionHandle,
    covdbHandle testHandle, int level, TraversalContext* ctx);

void traverseFsmCoverageObjects(covdbHandle obj, covdbHandle regionHandle,
    covdbHandle testHandle, int level, TraversalContext* ctx);

void traverseBranchCoverageObjects(covdbHandle obj, covdbHandle regionHandle,
    covdbHandle testHandle, int level, TraversalContext* ctx);

//按模块获得覆盖分数和VerifyPoint

// to do , pack VerifyPotint,search previous test
// 初始化服务（加载设计）
int service_init(const char* vdbName) {
    if (g_state.design != NULL) {
        printf("CoverageExtractToolServer: unloading previous design\n");
        covdb_unload(g_state.TglMetric);
        covdb_unload(g_state.FsmMetric);
        covdb_unload(g_state.BranchMetric);
        covdb_unload(g_state.ConditionMetric);
        covdb_unload(g_state.lineMetric);//按顺序卸载，避免段错误

        covdb_unload(g_state.test);
        covdb_unload(g_state.design);

        g_state.design = NULL;
        g_state.test = NULL;
        g_state.lineMetric = NULL;
        resetModuleShapeCache();
    }
    
    printf("CoverageExtractToolServer: loading design from %s\n", vdbName);
    g_state.design = loadDesign(vdbName);
    if (!g_state.design) {
        printf("CoverageExtractToolServer: error: failed to load design\n");
        return -1;
    }
    strncpy(g_state.currentVdb, vdbName, 511);
    g_state.currentVdb[511] = '\0';
    g_state.initialized = 1;
    resetModuleShapeCache();
    printf("CoverageExtractToolServer: design loaded successfully\n");
    return 0;
}

// 切换测试
int service_switch_test(const char* testName) {
    if (!g_state.design) {
        printf("CoverageExtractToolServer: error: no design loaded\n");
        return -1;
    }
    
    // 检查是否需要切换 test
    if (g_state.test != NULL && strcmp(g_state.currentTest, testName) == 0) {
        printf("CoverageExtractToolServer: using cached test: %s\n", testName);
        return 0;
    }
    
    if (g_state.test != NULL) {
        printf("CoverageExtractToolServer: unloading previous test\n");
        covdb_unload(g_state.test);
        g_state.test = NULL;
    }
    
    printf("CoverageExtractToolServer: loading test: %s\n", testName);
    g_state.test = loadTest(g_state.design, testName);
    if (!g_state.test) {
        printf("CoverageExtractToolServer: error: failed to load test\n");
        return -1;
    }
    
    g_state.lineMetric = findMetric(g_state.test,"Line");
    if (!g_state.lineMetric) {
        printf("CoverageExtractToolServer: error: failed to find line metric\n");
        return -1;
    }

    g_state.TglMetric = findMetric(g_state.test,"Tgl");
    if (!g_state.TglMetric) {
        printf("CoverageExtractToolServer: error: failed to find Tgl metric\n");
        return -1;
    }

    g_state.FsmMetric = findMetric(g_state.test,"Fsm");
    if (!g_state.FsmMetric) {
        printf("CoverageExtractToolServer: error: failed to find Fsm metric\n");
        return -1;
    }

    g_state.ConditionMetric = findMetric(g_state.test,"Condition");
    if (!g_state.ConditionMetric) {
        printf("CoverageExtractToolServer: error: failed to find Condition metric\n");
        return -1;
    }

    g_state.BranchMetric = findMetric(g_state.test,"Branch");
    if (!g_state.BranchMetric) {
        printf("CoverageExtractToolServer: error: failed to find Branch metric\n");
        return -1;
    }

    strncpy(g_state.currentTest, testName, 511);
    g_state.currentTest[511] = '\0';
    printf("CoverageExtractToolServer: test loaded successfully\n");
    return 0;
}

// 切换 VDB（重新加载设计和测试）
int service_switch_vdb(const char* vdbName, const char* testName) {
    printf("CoverageExtractToolServer: switching VDB to %s\n", vdbName);
    printf("CoverageExtractToolServer: switching TEST to %s\n", testName);
    // 重新初始化
    if (service_init(vdbName) != 0) {
        return -1;
    }
    
    // 加载测试
    if (service_switch_test(testName) != 0) {
        return -1;
    }
    
    return 0;
}

// 查询覆盖率
int service_query(const char* moduleName, int startLine, int endLine, char* output, int outputSize,CoverageParams params) {
    CoverageMetricSummary metricSummaries[5] = {
        {"line", "Line", 0, 0, 0},
        {"cond", "Condition", 0, 0, 0},
        {"tgl", "Tgl", 0, 0, 0},
        {"fsm", "Fsm", 0, 0, 0},
        {"branch", "Branch", 0, 0, 0},
    };
    CoverageMetricSummary moduleScoreSummaries[5] = {
        {"line", "Line", 0, 0, 0},
        {"cond", "Condition", 0, 0, 0},
        {"tgl", "Tgl", 0, 0, 0},
        {"fsm", "Fsm", 0, 0, 0},
        {"branch", "Branch", 0, 0, 0},
    };
    const int metricSummaryCount = sizeof(metricSummaries) / sizeof(metricSummaries[0]);
    float overallScore = 0.0f;
    int availableMetricCount = 0;
    char* qualifiedInstanceName = NULL;
    char* sourceFileName = NULL;

    if (output != NULL && outputSize > 0) {
        output[0] = '\0';
    }
    if (!g_state.design || !g_state.test || !g_state.lineMetric) {
        snprintf(output, outputSize, "{\"error\":\"Service not initialized, please provide vdb and test first\"}");
        return -1;
    }
    printf("======================Query Coverage Begin========================\n");
    printCoverageParams(params);
    printf("======================Line Coverage Begin========================\n");
    covdbHandle lineQualifiedTargetInstance = getQualifiedTargetInstance(g_state.design, g_state.lineMetric, (char*)moduleName);
    if (!lineQualifiedTargetInstance) {
        snprintf(output, outputSize, "{\"error\":\"Failed to get Line qualified target instance for module: %s\"}", moduleName);
        // free(cache);
        return -1;
    }
    qualifiedInstanceName = covdb_get_str(lineQualifiedTargetInstance, covdbFullName);
    sourceFileName = covdb_get_str(lineQualifiedTargetInstance, covdbFileName);
    printf("CoverageExtractToolServer: got qualified instance: %s\n", qualifiedInstanceName ? qualifiedInstanceName : "");
    if (sourceFileName != NULL && sourceFileName[0] != '\0') {
        printf("CoverageExtractToolServer: source file opened: %s\n", sourceFileName);
    }
    prepareModuleShapeCache(g_state.currentVdb, moduleName, sourceFileName);
    getCoverageData(lineQualifiedTargetInstance, g_state.test, startLine, endLine, output, &metricSummaries[0], traverseLineCoverageObjects);
    getModuleCoverageSummary(lineQualifiedTargetInstance, g_state.test, &moduleScoreSummaries[0]);
    printf("======================Line Coverage End========================\n");

    printf("======================Condition Coverage Begin========================\n");
    covdbHandle conditionQualifiedTargetInstance = getQualifiedTargetInstance(g_state.design, g_state.ConditionMetric, (char*)moduleName);
    if(!conditionQualifiedTargetInstance){
        snprintf(output, outputSize, "{\"error\":\"Failed to get Condition qualified target instance for module: %s\"}", moduleName);
        // free(cache);
        return -1;
    }
    getCoverageData(conditionQualifiedTargetInstance, g_state.test, startLine, endLine, output, &metricSummaries[1], traverseConditionCoverageObjects);
    getModuleCoverageSummary(conditionQualifiedTargetInstance, g_state.test, &moduleScoreSummaries[1]);
    printf("======================Condition Coverage End========================\n");

    printf("======================Tgl Coverage Begin========================\n");
    covdbHandle TglQualifiedTargetInstance = getQualifiedTargetInstance(g_state.design, g_state.TglMetric, (char*)moduleName);
    if(!TglQualifiedTargetInstance){
        snprintf(output, outputSize, "{\"error\":\"Failed to get Tgl qualified target instance for module: %s\"}", moduleName);
        // free(cache);
        return -1;
    }
    getCoverageData(TglQualifiedTargetInstance, g_state.test, startLine, endLine, output, &metricSummaries[2], traverseTglCoverageObjects);
    getModuleCoverageSummary(TglQualifiedTargetInstance, g_state.test, &moduleScoreSummaries[2]);
    printf("======================Tgl Coverage End========================\n");

    printf("======================Fsm Coverage Begin========================\n");
    covdbHandle FsmQualifiedTargetInstance = getQualifiedTargetInstance(g_state.design, g_state.FsmMetric, (char*)moduleName);
    if(!FsmQualifiedTargetInstance){
        snprintf(output, outputSize, "{\"error\":\"Failed to get Fsm qualified target instance for module: %s\"}", moduleName);
        // free(cache);
        return -1;
    }
    getCoverageData(FsmQualifiedTargetInstance, g_state.test, startLine, endLine, output, &metricSummaries[3], traverseFsmCoverageObjects);
    getModuleCoverageSummary(FsmQualifiedTargetInstance, g_state.test, &moduleScoreSummaries[3]);
    printf("======================Fsm Coverage End========================\n"); 

    printf("======================Branch Coverage Begin========================\n");
    covdbHandle branchQualifiedTargetInstance = getQualifiedTargetInstance(g_state.design, g_state.BranchMetric, (char*)moduleName);
    if(!branchQualifiedTargetInstance){
        snprintf(output, outputSize, "{\"error\":\"Failed to get Branch qualified target instance for module: %s\"}", moduleName);
        // free(cache);
        return -1;
    }
    getCoverageData(branchQualifiedTargetInstance, g_state.test, startLine, endLine, output, &metricSummaries[4], traverseBranchCoverageObjects);
    getModuleCoverageSummary(branchQualifiedTargetInstance, g_state.test, &moduleScoreSummaries[4]);
    printf("======================Branch Coverage End========================\n");
    printVpSummarySection(moduleName, startLine, endLine, qualifiedInstanceName, sourceFileName, metricSummaries, metricSummaryCount);
    printf("======================Instance Coverage Score========================\n");
    printf("instance name is : %s \n", qualifiedInstanceName ? qualifiedInstanceName : "");
    printf("rtl file name is : %s \n", sourceFileName ? sourceFileName : "");
    printf("instance's overall coverage score:\n");
    for(int i = 0; i < metricSummaryCount; i++){
        if(moduleScoreSummaries[i].coverable > 0){
            overallScore += getMetricSummaryScore(&moduleScoreSummaries[i]);
            availableMetricCount++;
        }
    }
    if (availableMetricCount > 0) {
        overallScore = overallScore / availableMetricCount;
        printf("Score : %.2f ",100 * overallScore);
    } else {
        printf("Score : nan ");
    }
    for(int i = 0; i < metricSummaryCount; i++){
        if(moduleScoreSummaries[i].coverable <= 0){
            printf("%s : nan ", moduleScoreSummaries[i].displayName);
            continue;
        }
        printf("%s : %.2f ", moduleScoreSummaries[i].displayName, 100 * getMetricSummaryScore(&moduleScoreSummaries[i]));
    }
    printf("\n");
    printf("======================Instance Coverage Score End========================\n");
    printf("======================Query Coverage End=========================\n");
    return 0;
}

// 清理服务
void service_cleanup() {
    if (g_state.test) {
        covdb_unload(g_state.test);
        g_state.test = NULL;
    }
    if (g_state.design) {
        covdb_unload(g_state.design);
        g_state.design = NULL;
    }
    g_state.lineMetric = NULL;
    g_state.initialized = 0;
    resetModuleShapeCache();
    printf("CoverageExtractToolServer: service cleaned up\n");
}

// 解析输入命令
int parseCommand(char* input, CoverageParams* params) {
    // 格式：<vdbPath> <testPath> <moduleName> <start-end>
    char vdbPath[512], testPath[512], moduleName[256], lineRange[64];
    
    int count = sscanf(input, "%511s %511s %255s %63s", vdbPath, testPath, moduleName, lineRange);
    if (count != 4) {
        return -1;
    }
    
    params->vdbName = strdup(vdbPath);
    params->testName = strdup(testPath);
    params->targetModuleName = strdup(moduleName);
    
    if (sscanf(lineRange, "%d-%d", &(params->startLineNo), &(params->endLineNo)) != 2) {
        free(params->vdbName);
        free(params->testName);
        free(params->targetModuleName);
        return -1;
    }
    
    return 0;
}

// 释放命令参数
void freeCommand(CoverageParams* params) {
    if (params->vdbName) free(params->vdbName);
    if (params->testName) free(params->testName);
    if (params->targetModuleName) free(params->targetModuleName);
    params->vdbName = params->testName = params->targetModuleName = NULL;
}

// 静态函数实现
static covdbHandle loadDesign(const char* vdbName) {
    covdbHandle design = covdb_load(covdbDesign, NULL, vdbName);
    sleep(1); // Wait for loading thread to complete

    if (design == NULL) {
        printf("CoverageExtractToolServer: error: the design specified is not valid!\n");
        return NULL;
    }
    printf("CoverageExtractToolServer: successful load design\n");
    return design;
}

static void unloadDesign(covdbHandle design) {
    if (design) covdb_unload(design);
}

static covdbHandle loadTest(covdbHandle design, const char* testName) {
    covdbHandle test = covdb_load(covdbTest, design, testName);

    if (test == NULL) {
        printf("CoverageExtractToolServer: error: the test specified is not valid! test name : %s\n", testName);
        return NULL;
    }
    printf("CoverageExtractToolServer: successful load test: %s\n", testName);
    return test;
}

static void unloadTest(covdbHandle test) {
    if (test) covdb_unload(test);
}

static covdbHandle findTargetDefinition(covdbHandle design, char* targetModuleName) {
    covdbHandle definitionsIterator = covdb_iterate(design, covdbDefinitions);
    covdbHandle aDefinition = covdb_scan(definitionsIterator);

    while (aDefinition != NULL) {
        char* name = covdb_get_str(aDefinition, covdbFullName);
        if (name && strcmp(name, targetModuleName) == 0) {
            // printf("CoverageExtractToolServer: found target module! input %s, found: %s\n", targetModuleName, name);
            covdb_release_handle(definitionsIterator);
            return aDefinition;
        }
        aDefinition = covdb_scan(definitionsIterator);
    }

    covdb_release_handle(definitionsIterator);
    printf("CoverageExtractToolServer: error: target module %s not found\n", targetModuleName);
    return NULL;
}

static covdbHandle findTargetInstance(covdbHandle definition) {
    covdbHandle targetInstancesIterator = covdb_iterate(definition, covdbInstances);
    covdbHandle targetInstance = covdb_scan(targetInstancesIterator);

    if (targetInstance != NULL) {
        // printf("CoverageExtractToolServer: found target instance : %s\n", covdb_get_str(targetInstance, covdbFullName));
    } else {
        printf("CoverageExtractToolServer: error: no instance found for definition\n");
    }

    covdb_release_handle(targetInstancesIterator);
    return targetInstance;
}

static covdbHandle findLineMetric(covdbHandle test) {
    covdbHandle metricsIterator = covdb_iterate(test, covdbMetrics);
    covdbHandle aMetric = covdb_scan(metricsIterator);

    while (aMetric != NULL) {
        char* name = covdb_get_str(aMetric, covdbFullName);
        if (name && strcmp(name, "Line") == 0) {
            printf("CoverageExtractToolServer: found Metric : %s\n", name);
            return aMetric;
        }
        aMetric = covdb_scan(metricsIterator);
    }

    printf("CoverageExtractToolServer: error: Line metric not found\n");
    return NULL;
}
static covdbHandle findMetric(covdbHandle test,char* metricName) {
    covdbHandle metricsIterator = covdb_iterate(test, covdbMetrics);
    covdbHandle aMetric = covdb_scan(metricsIterator);

    while (aMetric != NULL) {
        char* name = covdb_get_str(aMetric, covdbFullName);
        if (name && strcmp(name, metricName) == 0) {
            printf("CoverageExtractToolServer: found Metric : %s\n", name);
            return aMetric;
        }
        aMetric = covdb_scan(metricsIterator);
    }

    printf("CoverageExtractToolServer: error: %s metric not found\n",metricName);
    return NULL;
}
// 读取源文件指定行的内容
void printSourceLine(FILE* sourceFile, int lineNo) {
    if (sourceFile == NULL) {
        printf("  [Source file not available]");
        return;
    }
    
    rewind(sourceFile);
    char buffer[1024];
    int currentLine = 0;
    
    while (fgets(buffer, sizeof(buffer), sourceFile) != NULL) {
        currentLine++;
        if (currentLine == lineNo) {
            // 去除末尾换行符后打印
            buffer[strcspn(buffer, "\n")] = '\0';
            printf("  | %s", buffer);
            break;
        }
    }
}
void printIndent(int level) {
    for (int i = 0; i < level; i++) {
        printf("  ");
    }
}
static void resetModuleShapeCache(void) {
    memset(&g_moduleShape, 0, sizeof(g_moduleShape));
    g_moduleShape.fileId = -1;
    memset(g_branchSpecStack, 0, sizeof(g_branchSpecStack));
}

static void trimSpaces(char* text) {
    size_t start = 0;
    size_t len;
    if (text == NULL) return;
    len = strlen(text);
    while (start < len && isspace((unsigned char)text[start])) {
        start++;
    }
    while (len > start && isspace((unsigned char)text[len - 1])) {
        len--;
    }
    if (start > 0) {
        memmove(text, text + start, len - start);
    }
    text[len - start] = '\0';
}

static void xmlUnescape(const char* input, char* output, size_t outputSize) {
    size_t i = 0;
    size_t j = 0;
    if (outputSize == 0) return;
    while (input != NULL && input[i] != '\0' && j + 1 < outputSize) {
        if (strncmp(input + i, "&amp;", 5) == 0) {
            output[j++] = '&';
            i += 5;
        } else if (strncmp(input + i, "&apos;", 6) == 0) {
            output[j++] = '\'';
            i += 6;
        } else if (strncmp(input + i, "&quot;", 6) == 0) {
            output[j++] = '"';
            i += 6;
        } else if (strncmp(input + i, "&lt;", 4) == 0) {
            output[j++] = '<';
            i += 4;
        } else if (strncmp(input + i, "&gt;", 4) == 0) {
            output[j++] = '>';
            i += 4;
        } else {
            output[j++] = input[i++];
        }
    }
    output[j] = '\0';
    trimSpaces(output);
}

static int extractXmlAttrStr(const char* line, const char* attr, char* out, size_t outSize) {
    char pattern[64];
    const char* start;
    const char* end;
    size_t len;
    char raw[1024];

    if (line == NULL || attr == NULL || out == NULL || outSize == 0) return 0;
    snprintf(pattern, sizeof(pattern), "%s=\"", attr);
    start = strstr(line, pattern);
    if (start == NULL) return 0;
    start += strlen(pattern);
    end = strchr(start, '"');
    if (end == NULL) return 0;
    len = (size_t)(end - start);
    if (len >= sizeof(raw)) len = sizeof(raw) - 1;
    memcpy(raw, start, len);
    raw[len] = '\0';
    xmlUnescape(raw, out, outSize);
    return 1;
}

static int extractXmlAttrInt(const char* line, const char* attr, int* value) {
    char text[64];
    if (!extractXmlAttrStr(line, attr, text, sizeof(text))) return 0;
    *value = atoi(text);
    return 1;
}

static void appendText(char* buffer, size_t bufferSize, const char* fmt, ...) {
    va_list args;
    size_t used;
    int written;
    if (buffer == NULL || bufferSize == 0 || fmt == NULL) return;
    used = strlen(buffer);
    if (used >= bufferSize - 1) return;
    va_start(args, fmt);
    written = vsnprintf(buffer + used, bufferSize - used, fmt, args);
    va_end(args);
    if (written < 0) {
        buffer[used] = '\0';
    }
}

static void sanitizeSummaryValue(const char* input, char* output, size_t outputSize) {
    size_t i = 0;
    size_t j = 0;
    if (output == NULL || outputSize == 0) return;
    output[0] = '\0';
    if (input == NULL) return;
    while (input[i] != '\0' && j + 1 < outputSize) {
        char ch = input[i++];
        if (ch == '\n' || ch == '\r' || ch == '\t') {
            ch = ' ';
        }
        output[j++] = ch;
    }
    output[j] = '\0';
    trimSpaces(output);
}

static void normalizeBranchVector(const char* input, char* output, size_t outputSize) {
    size_t i;
    size_t j = 0;
    if (output == NULL || outputSize == 0) return;
    output[0] = '\0';
    if (input == NULL) return;
    for (i = 0; input[i] != '\0' && j + 1 < outputSize; i++) {
        if (input[i] == '0' || input[i] == '1') {
            output[j++] = input[i];
        }
    }
    output[j] = '\0';
}

static int getVectorBit(const char* vector, int positionFromRight) {
    size_t len;
    if (vector == NULL || positionFromRight <= 0) return 0;
    len = strlen(vector);
    if ((size_t)positionFromRight > len) return 0;
    return vector[len - (size_t)positionFromRight] == '1';
}

static int getVectorBitFromLeft(const char* vector, int positionFromLeft) {
    size_t len;
    if (vector == NULL || positionFromLeft <= 0) return 0;
    len = strlen(vector);
    if ((size_t)positionFromLeft > len) return 0;
    return vector[(size_t)positionFromLeft - 1] == '1';
}

static int decodeBranchExprState(const BranchExprMeta* expr, const char* vector) {
    if (expr == NULL || vector == NULL) return 0;
    if (getVectorBit(vector, expr->index)) return 1;
    if (getVectorBit(vector, expr->index + 1)) return -1;
    return 0;
}

static int decodeBranchExprStateFromLeft(const BranchExprMeta* expr, const char* vector) {
    if (expr == NULL || vector == NULL) return 0;
    if (getVectorBitFromLeft(vector, expr->index)) return 1;
    if (getVectorBitFromLeft(vector, expr->index + 1)) return -1;
    return 0;
}

static void shellQuote(const char* input, char* output, size_t outputSize) {
    size_t i;
    size_t j = 0;
    if (outputSize == 0) return;
    output[j++] = '\'';
    for (i = 0; input != NULL && input[i] != '\0' && j + 5 < outputSize; i++) {
        if (input[i] == '\'') {
            output[j++] = '\'';
            output[j++] = '\\';
            output[j++] = '\'';
            output[j++] = '\'';
        } else {
            output[j++] = input[i];
        }
    }
    if (j + 1 < outputSize) {
        output[j++] = '\'';
    }
    output[j] = '\0';
}

static FILE* openGzipTextFile(const char* path) {
    char quoted[1536];
    char cmd[MAX_CMD_LEN];
    shellQuote(path, quoted, sizeof(quoted));
    snprintf(cmd, sizeof(cmd), "gzip -dc %s", quoted);
    return popen(cmd, "r");
}

static void closeGzipTextFile(FILE* fp) {
    if (fp != NULL) {
        pclose(fp);
    }
}

static int parseTglShapeForModule(const char* vdbName, const char* moduleName, ModuleShapeCache* cache) {
    char path[1024];
    char line[4096];
    int inModule = 0;
    FILE* fp;

    snprintf(path, sizeof(path), "%s/snps/coverage/db/shape/tgl.verilog.shape.xml", vdbName);
    fp = openGzipTextFile(path);
    if (fp == NULL) return -1;

    while (fgets(line, sizeof(line), fp) != NULL) {
        char name[256];
        if (!inModule) {
            if (strstr(line, "<tgldef ") != NULL &&
                extractXmlAttrStr(line, "name", name, sizeof(name)) &&
                strcmp(name, moduleName) == 0) {
                inModule = 1;
            }
            continue;
        }
        if (strstr(line, "</tgldef>") != NULL) {
            break;
        }
        if (strstr(line, "<node ") != NULL || strstr(line, "<vectornode ") != NULL) {
            TglSignalMeta* meta;
            int fileId = -1;
            int lineNo = 0;
            int left = 0;
            int right = 0;
            int isVector = strstr(line, "<vectornode ") != NULL;

            if (cache->tglSignalCount >= MAX_TGL_SIGNALS) continue;
            meta = &cache->tglSignals[cache->tglSignalCount];
            memset(meta, 0, sizeof(*meta));
            if (!extractXmlAttrStr(line, "name", meta->name, sizeof(meta->name))) continue;
            extractXmlAttrInt(line, "line_num", &lineNo);
            extractXmlAttrInt(line, "file", &fileId);
            meta->lineNo = lineNo;
            meta->isVector = isVector;
            meta->width = 1;
            if (isVector &&
                extractXmlAttrInt(line, "left", &left) &&
                extractXmlAttrInt(line, "right", &right)) {
                meta->width = abs(left - right) + 1;
            }
            if (cache->fileId < 0 && fileId >= 0) {
                cache->fileId = fileId;
            }
            cache->tglSignalCount++;
        }
    }

    closeGzipTextFile(fp);
    return inModule ? 0 : -1;
}

static int parseFsmShapeForModule(const char* vdbName, const char* moduleName, ModuleShapeCache* cache) {
    char path[1024];
    char line[4096];
    int inModule = 0;
    FsmMeta* currentFsm = NULL;
    FILE* fp;

    snprintf(path, sizeof(path), "%s/snps/coverage/db/shape/fsm.verilog.shape.xml", vdbName);
    fp = openGzipTextFile(path);
    if (fp == NULL) return -1;

    while (fgets(line, sizeof(line), fp) != NULL) {
        char name[256];
        if (!inModule) {
            if (strstr(line, "<fsmdef ") != NULL &&
                extractXmlAttrStr(line, "name", name, sizeof(name)) &&
                strcmp(name, moduleName) == 0) {
                int fileId = -1;
                inModule = 1;
                if (extractXmlAttrInt(line, "file", &fileId) && cache->fileId < 0) {
                    cache->fileId = fileId;
                }
            }
            continue;
        }
        if (strstr(line, "</fsmdef>") != NULL) {
            break;
        }
        if (strstr(line, "<fsmfsm ") != NULL) {
            if (cache->fsmCount >= MAX_FSMS) continue;
            currentFsm = &cache->fsms[cache->fsmCount];
            memset(currentFsm, 0, sizeof(*currentFsm));
            extractXmlAttrStr(line, "name", currentFsm->currentName, sizeof(currentFsm->currentName));
            extractXmlAttrInt(line, "line", &currentFsm->lineNo);
            extractXmlAttrInt(line, "width", &currentFsm->width);
            cache->fsmCount++;
            continue;
        }
        if (strstr(line, "</fsmfsm>") != NULL) {
            currentFsm = NULL;
            continue;
        }
        if (currentFsm == NULL) continue;
        if (strstr(line, "<state ") != NULL) {
            FsmStateMeta* stateMeta;
            if (currentFsm->stateCount >= MAX_FSM_STATES) continue;
            stateMeta = &currentFsm->states[currentFsm->stateCount];
            memset(stateMeta, 0, sizeof(*stateMeta));
            extractXmlAttrStr(line, "name", stateMeta->name, sizeof(stateMeta->name));
            extractXmlAttrInt(line, "line", &stateMeta->lineNo);
            currentFsm->stateCount++;
        } else if (strstr(line, "<transition ") != NULL) {
            FsmTransitionMeta* transitionMeta;
            if (currentFsm->transitionCount >= MAX_FSM_TRANSITIONS) continue;
            transitionMeta = &currentFsm->transitions[currentFsm->transitionCount];
            memset(transitionMeta, 0, sizeof(*transitionMeta));
            extractXmlAttrInt(line, "fromid", &transitionMeta->fromId);
            extractXmlAttrInt(line, "toid", &transitionMeta->toId);
            extractXmlAttrInt(line, "line", &transitionMeta->lineNo);
            currentFsm->transitionCount++;
        }
    }

    closeGzipTextFile(fp);
    return inModule ? 0 : -1;
}

static int parseBranchShapeForFileId(const char* vdbName, int fileId, ModuleShapeCache* cache) {
    char path[1024];
    char line[4096];
    int inSpec = 0;
    int inCaseExpr = 0;
    BranchSpecMeta currentSpec;
    FILE* fp;

    snprintf(path, sizeof(path), "%s/snps/coverage/db/shape/branch.verilog.shape.xml", vdbName);
    fp = openGzipTextFile(path);
    if (fp == NULL) return -1;

    memset(&currentSpec, 0, sizeof(currentSpec));

    while (fgets(line, sizeof(line), fp) != NULL) {
        if (!inSpec) {
            if (strstr(line, "<branch_spec ") != NULL) {
                int specFileId = -1;
                extractXmlAttrInt(line, "file_id", &specFileId);
                if (fileId >= 0 && specFileId != fileId) {
                    continue;
                }
                memset(&currentSpec, 0, sizeof(currentSpec));
                currentSpec.fileId = specFileId;
                inSpec = 1;
                inCaseExpr = 0;
            }
            continue;
        }

        if (strstr(line, "</branch_spec>") != NULL) {
            if (currentSpec.rootLine > 0 &&
                currentSpec.rootExpr[0] != '\0' &&
                cache->branchSpecCount < MAX_BRANCH_SPECS) {
                cache->branchSpecs[cache->branchSpecCount++] = currentSpec;
            }
            inSpec = 0;
            inCaseExpr = 0;
            continue;
        }

        if (strstr(line, "<branch_cexpr ") != NULL) {
            currentSpec.isCase = 1;
            extractXmlAttrInt(line, "id", &currentSpec.rootLine);
            extractXmlAttrStr(line, "exprstr", currentSpec.rootExpr, sizeof(currentSpec.rootExpr));
            inCaseExpr = 1;
            continue;
        }
        if (strstr(line, "</branch_cexpr>") != NULL) {
            inCaseExpr = 0;
            continue;
        }
        if (inCaseExpr && strstr(line, "<branch_citem ") != NULL) {
            BranchCaseItemMeta* item;
            if (currentSpec.caseItemCount >= MAX_BRANCH_CASE_ITEMS) continue;
            item = &currentSpec.caseItems[currentSpec.caseItemCount];
            memset(item, 0, sizeof(*item));
            extractXmlAttrInt(line, "index", &item->index);
            extractXmlAttrInt(line, "line_num", &item->lineNo);
            extractXmlAttrStr(line, "name", item->name, sizeof(item->name));
            currentSpec.caseItemCount++;
            continue;
        }
        if (strstr(line, "<branch_expr ") != NULL) {
            BranchExprMeta* expr;
            if (currentSpec.exprCount >= MAX_BRANCH_EXPRS) continue;
            expr = &currentSpec.exprs[currentSpec.exprCount];
            memset(expr, 0, sizeof(*expr));
            extractXmlAttrInt(line, "id", &expr->lineNo);
            extractXmlAttrInt(line, "index", &expr->index);
            extractXmlAttrInt(line, "parent_bit", &expr->parentBit);
            extractXmlAttrInt(line, "true_clause_line", &expr->trueClauseLine);
            extractXmlAttrInt(line, "false_clause_line", &expr->falseClauseLine);
            extractXmlAttrStr(line, "exprstr", expr->expr, sizeof(expr->expr));
            if (!currentSpec.isCase && currentSpec.rootLine == 0) {
                currentSpec.rootLine = expr->lineNo;
                strncpy(currentSpec.rootExpr, expr->expr, sizeof(currentSpec.rootExpr) - 1);
                currentSpec.rootExpr[sizeof(currentSpec.rootExpr) - 1] = '\0';
            }
            currentSpec.exprCount++;
        }
    }

    closeGzipTextFile(fp);
    return cache->branchSpecCount > 0 ? 0 : -1;
}

static int resolveSourceFileId(const char* vdbName, const char* sourceFile) {
    char path[1024];
    char line[4096];
    FILE* fp;
    if (vdbName == NULL || sourceFile == NULL || sourceFile[0] == '\0') return -1;
    snprintf(path, sizeof(path), "%s/snps/coverage/db/auxiliary/verilog.sourceinfo.xml", vdbName);
    fp = fopen(path, "r");
    if (fp == NULL) return -1;
    while (fgets(line, sizeof(line), fp) != NULL) {
        char name[1024];
        int fileId = -1;
        if (strstr(line, "<fileinfo ") == NULL) continue;
        if (!extractXmlAttrStr(line, "name", name, sizeof(name))) continue;
        if (strcmp(name, sourceFile) != 0) continue;
        if (extractXmlAttrInt(line, "id", &fileId)) {
            fclose(fp);
            return fileId;
        }
    }
    fclose(fp);
    return -1;
}

static int prepareModuleShapeCache(const char* vdbName, const char* moduleName, const char* sourceFile) {
    int resolvedFileId = -1;
    if (g_moduleShape.loaded &&
        strcmp(g_moduleShape.vdbPath, vdbName) == 0 &&
        strcmp(g_moduleShape.moduleName, moduleName) == 0 &&
        strcmp(g_moduleShape.sourceFile, sourceFile ? sourceFile : "") == 0) {
        return 0;
    }

    resetModuleShapeCache();
    strncpy(g_moduleShape.vdbPath, vdbName, sizeof(g_moduleShape.vdbPath) - 1);
    strncpy(g_moduleShape.moduleName, moduleName, sizeof(g_moduleShape.moduleName) - 1);
    if (sourceFile != NULL) {
        strncpy(g_moduleShape.sourceFile, sourceFile, sizeof(g_moduleShape.sourceFile) - 1);
    }
    g_moduleShape.fileId = -1;

    parseTglShapeForModule(vdbName, moduleName, &g_moduleShape);
    parseFsmShapeForModule(vdbName, moduleName, &g_moduleShape);
    if (sourceFile != NULL && sourceFile[0] != '\0') {
        resolvedFileId = resolveSourceFileId(vdbName, sourceFile);
        if (resolvedFileId >= 0) {
            g_moduleShape.fileId = resolvedFileId;
        }
    }
    parseBranchShapeForFileId(vdbName, g_moduleShape.fileId, &g_moduleShape);

    g_moduleShape.loaded = 1;
    return 0;
}

static const TglSignalMeta* findTglSignalMeta(const char* name, int lineNo) {
    int i;
    const TglSignalMeta* fallback = NULL;
    for (i = 0; i < g_moduleShape.tglSignalCount; i++) {
        const TglSignalMeta* meta = &g_moduleShape.tglSignals[i];
        if (strcmp(meta->name, name) != 0) continue;
        if (lineNo > 0 && meta->lineNo == lineNo) return meta;
        if (fallback == NULL) fallback = meta;
    }
    return fallback;
}

static const FsmMeta* findFsmMeta(const char* name, int lineNo) {
    int i;
    const FsmMeta* fallback = NULL;
    for (i = 0; i < g_moduleShape.fsmCount; i++) {
        const FsmMeta* meta = &g_moduleShape.fsms[i];
        if (strcmp(meta->currentName, name) != 0) continue;
        if (lineNo > 0 && meta->lineNo == lineNo) return meta;
        if (fallback == NULL) fallback = meta;
    }
    return fallback;
}

static const BranchSpecMeta* findBranchSpecMeta(const char* name, int lineNo) {
    int i;
    const BranchSpecMeta* fallback = NULL;
    for (i = 0; i < g_moduleShape.branchSpecCount; i++) {
        const BranchSpecMeta* meta = &g_moduleShape.branchSpecs[i];
        if (lineNo > 0 && meta->rootLine != lineNo) continue;
        if (name != NULL && name[0] != '\0' && strcmp(meta->rootExpr, name) == 0) {
            return meta;
        }
        if (fallback == NULL) fallback = meta;
    }
    return fallback;
}

static const BranchSpecMeta* findBranchSpecMetaByChildLine(int lineNo) {
    int i;
    int j;
    if (lineNo <= 0) return NULL;
    for (i = 0; i < g_moduleShape.branchSpecCount; i++) {
        const BranchSpecMeta* meta = &g_moduleShape.branchSpecs[i];
        for (j = 0; j < meta->exprCount; j++) {
            if (meta->exprs[j].trueClauseLine == lineNo || meta->exprs[j].falseClauseLine == lineNo) {
                return meta;
            }
        }
        for (j = 0; j < meta->caseItemCount; j++) {
            if (meta->caseItems[j].lineNo == lineNo) {
                return meta;
            }
        }
    }
    return NULL;
}

static const char* findFsmStateName(const FsmMeta* meta, int stateId) {
    if (meta == NULL || stateId < 0 || stateId >= meta->stateCount) {
        return "<unknown>";
    }
    return meta->states[stateId].name;
}

static int decodeBranchVectorWithOrder(const BranchSpecMeta* spec, const char* vector, char* decoded, size_t decodedSize, int fromRight) {
    int i;
    int emitted = 0;

    if (decodedSize == 0) return 0;
    decoded[0] = '\0';
    if (spec == NULL || vector == NULL) {
        return 0;
    }

    if (spec->isCase) {
        const BranchCaseItemMeta* selected = NULL;
        for (i = 0; i < spec->caseItemCount; i++) {
            int hit = fromRight
                ? getVectorBit(vector, spec->caseItems[i].index)
                : getVectorBitFromLeft(vector, spec->caseItems[i].index);
            if (hit) {
                selected = &spec->caseItems[i];
                break;
            }
        }
        if (selected != NULL) {
            appendText(decoded, decodedSize, "case(%s)=%s", spec->rootExpr, selected->name);
            emitted = 1;
        } else {
            appendText(decoded, decodedSize, "case(%s)=<unknown>", spec->rootExpr);
            emitted = 1;
        }
    }

    for (i = 0; i < spec->exprCount; i++) {
        int state = fromRight
            ? decodeBranchExprState(&spec->exprs[i], vector)
            : decodeBranchExprStateFromLeft(&spec->exprs[i], vector);
        if (state == 0) continue;
        appendText(decoded, decodedSize, "%s%s=%s",
                   emitted ? "; " : "",
                   spec->exprs[i].expr,
                   state > 0 ? "true" : "false");
        emitted = 1;
    }

    if (!emitted) {
        decoded[0] = '\0';
        return 0;
    }
    return emitted;
}

static int decodeBranchVector(const BranchSpecMeta* spec, const char* vector, char* decoded, size_t decodedSize) {
    int emitted = 0;
    if (decoded == NULL || decodedSize == 0) return 0;
    decoded[0] = '\0';
    if (spec == NULL || vector == NULL) {
        snprintf(decoded, decodedSize, "%s", vector ? vector : "<unknown>");
        return 0;
    }
    emitted = decodeBranchVectorWithOrder(spec, vector, decoded, decodedSize, 1);
    if (emitted > 0) return emitted;
    emitted = decodeBranchVectorWithOrder(spec, vector, decoded, decodedSize, 0);
    if (emitted > 0) return emitted;
    snprintf(decoded, decodedSize, "%s", vector);
    return 0;
}

static int isLineWithinRange(int lineNo, const TraversalContext* ctx) {
    if (ctx == NULL || lineNo <= 0) return 0;
    return lineNo >= ctx->startLineNo && lineNo <= ctx->endLineNo;
}

static void recordMetricCoverage(TraversalContext* ctx, int covered, int coverable) {
    if (ctx == NULL || ctx->summary == NULL || coverable <= 0) return;
    ctx->summary->covered += covered;
    ctx->summary->coverable += coverable;
    ctx->summary->matchedObjects++;
}

static void recordLineCoverage(TraversalContext* ctx, int lineNo, int covered) {
    int index;
    if (ctx == NULL || ctx->summary == NULL || ctx->lineStates == NULL) return;
    if (!isLineWithinRange(lineNo, ctx)) return;
    index = lineNo - ctx->startLineNo;
    if (index < 0 || index >= ctx->lineStateCapacity) return;
    if (ctx->lineStates[index] < 0) {
        ctx->lineStates[index] = covered ? 1 : 0;
        ctx->summary->coverable++;
        ctx->summary->matchedObjects++;
        if (covered) {
            ctx->summary->covered++;
        }
        return;
    }
    if (covered && ctx->lineStates[index] == 0) {
        ctx->lineStates[index] = 1;
        ctx->summary->covered++;
    }
}

static float getMetricSummaryScore(const CoverageMetricSummary* summary) {
    if (summary == NULL || summary->coverable <= 0) return 0.0f;
    return (float)summary->covered / (float)summary->coverable;
}

static void printVpSummarySection(const char* moduleName,
    int startLineNo,
    int endLineNo,
    const char* qualifiedInstance,
    const char* sourceFile,
    CoverageMetricSummary* summaries,
    int summaryCount) {
    char safeModule[256];
    char safeQualifiedInstance[1024];
    char safeSourceFile[1024];
    float overallScore = 0.0f;
    int availableMetricCount = 0;
    int i;

    sanitizeSummaryValue(moduleName, safeModule, sizeof(safeModule));
    sanitizeSummaryValue(qualifiedInstance, safeQualifiedInstance, sizeof(safeQualifiedInstance));
    sanitizeSummaryValue(sourceFile, safeSourceFile, sizeof(safeSourceFile));

    printf("======================VP Summary Begin========================\n");
    printf("VP_QUERY\tmodule\t%s\trange\t%d-%d\tqualified_instance\t%s\tsource_file\t%s\n",
           safeModule,
           startLineNo,
           endLineNo,
           safeQualifiedInstance,
           safeSourceFile);

    for (i = 0; i < summaryCount; i++) {
        float score = getMetricSummaryScore(&summaries[i]);
        if (summaries[i].coverable > 0) {
            overallScore += score;
            availableMetricCount++;
        }
        printf("VP_METRIC\tkind\t%s\tcovered\t%d\tcoverable\t%d\tpct\t%.2f\tmatched\t%d\n",
               summaries[i].kindKey,
               summaries[i].covered,
               summaries[i].coverable,
               summaries[i].coverable > 0 ? score * 100.0f : 0.0f,
               summaries[i].matchedObjects);
    }

    printf("VP_OVERALL\tpct\t");
    if (availableMetricCount > 0) {
        printf("%.2f", (overallScore / availableMetricCount) * 100.0f);
    } else {
        printf("0.00");
    }
    printf("\tmetric_count\t%d\n", availableMetricCount);
    printf("======================VP Summary End========================\n");
}
static int hasChildObjects(covdbHandle obj) {
    covdbHandle childIterator = covdb_iterate(obj, covdbObjects);
    covdbHandle child = NULL;
    int hasChild = 0;
    if (childIterator == NULL) return 0;
    child = covdb_scan(childIterator);
    hasChild = (child != NULL);
    covdb_release_handle(childIterator);
    return hasChild;
}

static void printObjectCoverageStatus(int covered, int coverable) {
    if (covered == coverable) {
        printf("covered (%d/%d)", covered, coverable);
    } else {
        printf("not covered (%d/%d)", covered, coverable);
    }
}

static const char* getPreferredString(char* primary, char* fallback1, char* fallback2) {
    if (primary != NULL && primary[0] != '\0') return primary;
    if (fallback1 != NULL && fallback1[0] != '\0') return fallback1;
    if (fallback2 != NULL && fallback2[0] != '\0') return fallback2;
    return NULL;
}

static void printUcapiDetailSuffix(covdbHandle obj) {
    char* valueName = covdb_get_str(obj, covdbValueName);
    char* valueStr = covdb_get_str(obj, covdbValueStr);
    char* davinciStr = covdb_get_str(obj, covdbDavinciStr);
    const char* detail = getPreferredString(valueName, valueStr, davinciStr);
    if (detail != NULL) {
        printf(" ; ucapi=%s", detail);
    }
}

static void printSourceSnippetIfAny(FILE* sourceFile, int lineNo) {
    if (lineNo > 0) {
        printSourceLine(sourceFile, lineNo);
    }
}

static void printBranchCross(covdbHandle obj, covdbHandle regionHandle, covdbHandle testHandle, int level) {
    int coverable = covdb_get(obj, regionHandle, NULL, covdbCoverable);
    int covered = covdb_get(obj, regionHandle, testHandle, covdbCovered);
    int lineNo = covdb_get(obj, regionHandle, testHandle, covdbLineNo);
    char* rawName = covdb_get_str(obj, covdbFullName);
    char normalizedVector[MAX_DECODE_TEXT];
    char decoded[MAX_DECODE_TEXT];
    char* valueName = covdb_get_str(obj, covdbValueName);
    char* valueStr = covdb_get_str(obj, covdbValueStr);
    char* davinciStr = covdb_get_str(obj, covdbDavinciStr);
    const char* vectorText = getPreferredString(valueName, valueStr, davinciStr);
    const BranchSpecMeta* parentSpec = NULL;
    int decodedCount = 0;

    if (level > 0) {
        parentSpec = g_branchSpecStack[level - 1];
    }
    if (vectorText == NULL || vectorText[0] == '\0') {
        vectorText = rawName;
    }
    normalizeBranchVector(vectorText, normalizedVector, sizeof(normalizedVector));
    if (normalizedVector[0] == '\0') {
        normalizeBranchVector(rawName, normalizedVector, sizeof(normalizedVector));
    }
    if (normalizedVector[0] == '\0' && vectorText != NULL) {
        strncpy(normalizedVector, vectorText, sizeof(normalizedVector) - 1);
        normalizedVector[sizeof(normalizedVector) - 1] = '\0';
    }

    decodedCount = decodeBranchVector(parentSpec, normalizedVector, decoded, sizeof(decoded));
    if (decodedCount == 0) {
        const BranchSpecMeta* fallbackSpec = findBranchSpecMetaByChildLine(lineNo);
        if (fallbackSpec != NULL && fallbackSpec != parentSpec) {
            decodedCount = decodeBranchVector(fallbackSpec, normalizedVector, decoded, sizeof(decoded));
        }
    }

    (void)covered;
    (void)coverable;
    (void)level;
    (void)decoded;
    (void)decodedCount;
    (void)lineNo;
    (void)valueName;
    (void)valueStr;
    (void)davinciStr;
}

static void printTglContainer(covdbHandle obj, covdbHandle regionHandle, covdbHandle testHandle, int level, FILE* sourceFile) {
    int coverable = covdb_get(obj, regionHandle, NULL, covdbCoverable);
    int covered = covdb_get(obj, regionHandle, testHandle, covdbCovered);
    int lineNo = covdb_get(obj, regionHandle, testHandle, covdbLineNo);
    int width = covdb_get(obj, regionHandle, NULL, covdbWidth);
    char* name = covdb_get_str(obj, covdbFullName);
    const TglSignalMeta* meta = findTglSignalMeta(name ? name : "", lineNo);

    if (meta != NULL && width <= 0) {
        width = meta->width;
    }

    printIndent(level);
    if (level == 0 && (strcmp(name, "port") == 0 || strcmp(name, "signal") == 0)) {
        return;
    }

    if (coverable > 0 && covered >= coverable) {
        return;
    }

    printf("Toggle %s: %s", width > 1 ? "Vector" : "Signal", name ? name : "<unnamed>");
    if (lineNo > 0) {
        printf(" ; line=%d", lineNo);
    }
    if (width > 1) {
        printf(" ; width=%d", width);
        printf(" ; directional bins=%d/%d", covered, coverable);
    } else {
        printf(" ; ");
        if (coverable == 2) {
            if (covered == 2) {
                printf("0->1 and 1->0 both observed");
            } else if (covered == 1) {
                printf("only one toggle direction observed");
            } else {
                printf("no toggle direction observed");
            }
            printf(" (%d/%d)", covered, coverable);
        } else {
            printObjectCoverageStatus(covered, coverable);
        }
    }
    printUcapiDetailSuffix(obj);
    printf("\n");
}

static void printFsmContainer(covdbHandle obj, covdbHandle regionHandle, covdbHandle testHandle, int level, FILE* sourceFile) {
    int coverable = covdb_get(obj, regionHandle, NULL, covdbCoverable);
    int covered = covdb_get(obj, regionHandle, testHandle, covdbCovered);
    int lineNo = covdb_get(obj, regionHandle, testHandle, covdbLineNo);
    char* name = covdb_get_str(obj, covdbFullName);
    const FsmMeta* meta = findFsmMeta(name ? name : "", lineNo);
    int i;

    printIndent(level);
    printf("FSM: %s", name ? name : "<unnamed>");
    if (lineNo > 0) {
        printf(" ; line=%d", lineNo);
    }
    printf(" ; ");
    printObjectCoverageStatus(covered, coverable);
    if (meta != NULL) {
        printf(" ; states=%d ; transitions=%d", meta->stateCount, meta->transitionCount);
    }
    printUcapiDetailSuffix(obj);
    printSourceSnippetIfAny(sourceFile, lineNo);
    printf("\n");
}

void traverseBranchCoverageObjects(covdbHandle obj, covdbHandle regionHandle,
                             covdbHandle testHandle, int level, TraversalContext* ctx){
    if (obj == NULL) return;
    {
        char* typeStr = getHdlType(obj, regionHandle);
        char* name = covdb_get_str(obj, covdbFullName);
        int lineNo = covdb_get(obj, regionHandle, testHandle, covdbLineNo);

        if (level != 0 && lineNo > 0 && !isLineWithinRange(lineNo, ctx)) return;

        if (strcmp(typeStr, "covdbContainer") == 0) {
            int coverable = covdb_get(obj, regionHandle, NULL, covdbCoverable);
            int covered = covdb_get(obj, regionHandle, testHandle, covdbCovered);
            const BranchSpecMeta* spec = findBranchSpecMeta(name ? name : "", lineNo);

            g_branchSpecStack[level] = spec;
            if (isLineWithinRange(lineNo, ctx)) {
                recordMetricCoverage(ctx, covered, coverable);
            }
            if (lineNo > 0) {
                printIndent(level);
                printf("Branch: %s", name ? name : "<unnamed>");
                printf(" ; line=%d", lineNo);
                printf(" ; ");
                printObjectCoverageStatus(covered, coverable);
                printUcapiDetailSuffix(obj);
                printSourceSnippetIfAny(ctx ? ctx->sourceFile : NULL, lineNo);
                printf("\n");
            }
            g_branchSpecStack[level] = NULL;
            return;
        }

        if (strcmp(typeStr, "covdbCross") == 0) {
            return;
        }
    }
}
void traverseTglCoverageObjects(covdbHandle obj, covdbHandle regionHandle,
                             covdbHandle testHandle, int level, TraversalContext* ctx){
    if (obj == NULL) return;
    {
        char* typeStr = getHdlType(obj, regionHandle);
        int lineNo = covdb_get(obj, regionHandle, testHandle, covdbLineNo);

        if (level != 0 && lineNo > 0 && !isLineWithinRange(lineNo, ctx)) return;

        if (strcmp(typeStr, "covdbContainer") == 0) {
            covdbHandle childIterator = covdb_iterate(obj, covdbObjects);
            covdbHandle child = NULL;
            int coverable = covdb_get(obj, regionHandle, NULL, covdbCoverable);
            int covered = covdb_get(obj, regionHandle, testHandle, covdbCovered);
            if (isLineWithinRange(lineNo, ctx)) {
                recordMetricCoverage(ctx, covered, coverable);
            }
            if (level == 1 || (level == 0 && lineNo > 0)) {
                printTglContainer(obj, regionHandle, testHandle, level, ctx ? ctx->sourceFile : NULL);
            }
            if (level == 0 && childIterator != NULL) {
                child = covdb_scan(childIterator);
                while (child != NULL) {
                    traverseTglCoverageObjects(child, regionHandle, testHandle, level + 1, ctx);
                    child = covdb_scan(childIterator);
                }
            }
            if (childIterator != NULL) {
                covdb_release_handle(childIterator);
            }
            return;
        }
    }
}
void traverseFsmCoverageObjects(covdbHandle obj, covdbHandle regionHandle,
                             covdbHandle testHandle, int level, TraversalContext* ctx){
    if (obj == NULL) return;
    {
        char* typeStr = getHdlType(obj, regionHandle);
        int lineNo = covdb_get(obj, regionHandle, testHandle, covdbLineNo);

        if (level != 0 && lineNo > 0 && !isLineWithinRange(lineNo, ctx)) return;

        if (strcmp(typeStr, "covdbContainer") == 0) {
            int coverable = covdb_get(obj, regionHandle, NULL, covdbCoverable);
            int covered = covdb_get(obj, regionHandle, testHandle, covdbCovered);
            if (isLineWithinRange(lineNo, ctx)) {
                recordMetricCoverage(ctx, covered, coverable);
            }
            if (level == 0) {
                printFsmContainer(obj, regionHandle, testHandle, level, ctx ? ctx->sourceFile : NULL);
            }
            return;
        }
    }
}
void traverseLineCoverageObjects(covdbHandle obj, covdbHandle regionHandle,
                             covdbHandle testHandle, int level, TraversalContext* ctx){

    if(obj==NULL)return;

    char* objTypeStr = getHdlType(obj,regionHandle);
    int lineNo = covdb_get(obj, regionHandle, testHandle, covdbLineNo);
    if(level != 0 && lineNo > 0 && !isLineWithinRange(lineNo, ctx)) return;

    if(strcmp(objTypeStr,"covdbContainer")==0){
        covdbHandle childIterator = covdb_iterate(obj, covdbObjects);
        covdbHandle child = covdb_scan(childIterator);
        while(child!=NULL){
            traverseLineCoverageObjects(child, regionHandle, testHandle, level + 1, ctx);
            child = covdb_scan(childIterator);
        }
        covdb_release_handle(childIterator);
    }else if(strcmp(objTypeStr,"covdbBlock")==0){
        int cover = covdb_get(obj, regionHandle, testHandle, covdbCovered);
        if (!isLineWithinRange(lineNo, ctx)) return;
        recordLineCoverage(ctx, lineNo, cover);
        printf("Line %d cover status: ",lineNo);
        if(cover){printf("Yes");}else{printf("No ");}
        printSourceLine(ctx ? ctx->sourceFile : NULL, lineNo);
        printf("\n");
    }
}
void traverseConditionCoverageObjects(covdbHandle obj, covdbHandle regionHandle,
                             covdbHandle testHandle, int level, TraversalContext* ctx) {
    if (obj == NULL) return;
    
    char* typeStr = getHdlType(obj, regionHandle);
    char* name = covdb_get_str(obj, covdbFullName);
    int lineNo = covdb_get(obj, regionHandle, testHandle, covdbLineNo);
    if(level != 0 && lineNo > 0 && !isLineWithinRange(lineNo, ctx)) return;

    if(strcmp(typeStr, "covdbCross") == 0){
        int coverable = covdb_get(obj, regionHandle, NULL, covdbCoverable);
        int covered = covdb_get(obj, regionHandle, testHandle, covdbCovered);
        if (isLineWithinRange(lineNo, ctx)) {
            recordMetricCoverage(ctx, covered, coverable);
        }
        printIndent(level);
        printf("Sub Condition : %s ", name ? name : "<unnamed>");
        printf("; cover status : ");
        if (covered == coverable) {
            printf("condition coverd! (%d/%d) ", covered, coverable);
        } else {
            printf("condition not coverd! (%d/%d) ", covered, coverable);
        }
        printf("\n");
        return;
    }
    if (strcmp(typeStr, "covdbContainer") == 0 ) {
        printIndent(level);
        printf("situation : %s ", name ? name : "<unnamed>");
        if (lineNo > 0) {
            printf("lineNo : %d", lineNo);
        }
        printf("\n");
        covdbHandle childIterator = covdb_iterate(obj, covdbObjects);
        if (childIterator != NULL) {
            covdbHandle child = covdb_scan(childIterator);
            while (child != NULL) {
                traverseConditionCoverageObjects(child, regionHandle, testHandle, level + 1, ctx);
                child = covdb_scan(childIterator);
            }
            covdb_release_handle(childIterator);
        }
    }
}
// /home/c910/wangyahao/openc910/smart_run/tb1/my_forcerv_test /home/c910/wangyahao/openc910/smart_run/tb1/my_forcerv_test.vdb/test1 ct_ifu_l1_refill 0-5000
static float getCoverageData(covdbHandle qualifiedTargetInstance,
    covdbHandle test,
    int startLineNo,
    int endLineNo,
    char* output,
    CoverageMetricSummary* summary,
    traverseFunction traverseFunction){
    covdbHandle rootIterator = covdb_iterate(qualifiedTargetInstance, covdbObjects);
    covdbHandle rootObj = covdb_scan(rootIterator);
    char* fileName = covdb_get_str(qualifiedTargetInstance,covdbFileName);
    FILE* sourceFile = fopen(fileName, "r");
    TraversalContext ctx;
    int lineStateCapacity = 0;
    int i;
    (void)output;

    memset(&ctx, 0, sizeof(ctx));
    ctx.startLineNo = startLineNo;
    ctx.endLineNo = endLineNo;
    ctx.sourceFile = sourceFile;
    ctx.summary = summary;

    if (summary != NULL) {
        summary->covered = 0;
        summary->coverable = 0;
        summary->matchedObjects = 0;
        if (strcmp(summary->kindKey, "line") == 0 && endLineNo >= startLineNo) {
            lineStateCapacity = endLineNo - startLineNo + 1;
            ctx.lineStates = (int*)malloc(sizeof(int) * (size_t)lineStateCapacity);
            if (ctx.lineStates != NULL) {
                ctx.lineStateCapacity = lineStateCapacity;
                for (i = 0; i < lineStateCapacity; i++) {
                    ctx.lineStates[i] = -1;
                }
            }
        }
    }

    if (sourceFile == NULL) {
        printf("CoverageExtractToolServer: warning: failed to open source file: %s\n", fileName);
    }
    while(rootObj != NULL){
        traverseFunction(rootObj, qualifiedTargetInstance, test, 0, &ctx);
        rootObj = covdb_scan(rootIterator);
    }
    if(rootIterator!=NULL){
        covdb_release_handle(rootIterator);
    }
    // 关闭文件
    if (sourceFile != NULL) {
        fclose(sourceFile);
    }
    if (ctx.lineStates != NULL) {
        free(ctx.lineStates);
    }
    return getMetricSummaryScore(summary);
}

static void getModuleCoverageSummary(covdbHandle qualifiedTargetInstance,
    covdbHandle test,
    CoverageMetricSummary* summary) {
    covdbHandle rootIterator;
    covdbHandle rootObj;

    if (summary == NULL) return;
    summary->covered = 0;
    summary->coverable = 0;
    summary->matchedObjects = 0;
    if (qualifiedTargetInstance == NULL) return;

    rootIterator = covdb_iterate(qualifiedTargetInstance, covdbObjects);
    if (rootIterator == NULL) return;

    rootObj = covdb_scan(rootIterator);
    while (rootObj != NULL) {
        int coverable = covdb_get(rootObj, qualifiedTargetInstance, NULL, covdbCoverable);
        int covered = covdb_get(rootObj, qualifiedTargetInstance, test, covdbCovered);
        if (coverable > 0) {
            summary->coverable += coverable;
            summary->covered += covered;
            summary->matchedObjects++;
        }
        rootObj = covdb_scan(rootIterator);
    }
    covdb_release_handle(rootIterator);
}


static covdbHandle getQualifiedTargetInstance(covdbHandle design, covdbHandle Metric, char* targetModuleName) {
    covdbHandle targetDefinition = findTargetDefinition(design, targetModuleName);
    if (!targetDefinition) {
        return NULL;
    }
    covdbHandle targetInstance = findTargetInstance(targetDefinition);
    if (!targetInstance) {
        return NULL;
    }
    covdbHandle qualifiedTargetInstance = covdb_get_qualified_handle(targetInstance, Metric, covdbIdentity);
    // printf("CoverageExtractToolServer: got qualified instance: %s\n", covdb_get_str(qualifiedTargetInstance, covdbFullName));
    return qualifiedTargetInstance;
}

static void initCache(CoverStatus* cache, int size) {
    for (int i = 0; i < size; i++) {
        cache[i].lineNo = 0;
        cache[i].coverState = 0;
    }
}

char* getHdlType(covdbHandle hdl ,covdbHandle regionHdl){
	covdbObjTypesT objty = covdb_get(hdl, regionHdl, NULL,covdbType);
	char* typeStr;
	switch(objty){
	    case covdbNullHandle             :typeStr = "covdbNullHandle "; break;
		case covdbInternal      	     :typeStr = "covdbInternal"; break;
		case covdbDesign        	     :typeStr = "covdbDesign"; break;
		case covdbIterator      	     :typeStr = "covdbIterator"; break;
		case covdbContainer     	     :typeStr = "covdbContainer"; break;
		case covdbMetric        	     :typeStr = "covdbMetric"; break;
		case covdbSourceInstance         :typeStr = "covdbSourceInstance"; break;
		case covdbSourceDefinition       :typeStr = "covdbSourceDefinition"; break;
		case covdbBlock     	         :typeStr = "covdbBlock"; break;
		case covdbIntegerValue      	 :typeStr = "covdbIntegerValue"; break;
		case covdbScalarValue       	 :typeStr = "covdbScalarValue"; break;
		case covdbVectorValue       	 :typeStr = "covdbVectorValue"; break;
		case covdbIntervalValue     	 :typeStr = "covdbIntervalValue"; break;
		case covdbBDDValue      	     :typeStr = "covdbBDDValue"; break;
		case covdbCross     	         :typeStr = "covdbCross"; break;
		case covdbSequence      	     :typeStr = "covdbSequence"; break;
		case covdbAnnotation        	 :typeStr = "covdbAnnotation"; break;
		case covdbTest      	         :typeStr = "covdbTest"; break;
		case covdbTestName      	     :typeStr = "covdbTestName"; break;
		case covdbInterval      	     :typeStr = "covdbInterval"; break;
		case covdbExcludeFile       	 :typeStr = "covdbExcludeFile"; break;
		case covdbHierFile      	     :typeStr = "covdbHierFile"; break;
		case covdbEditFile      	     :typeStr = "covdbEditFile"; break;
		case covdbBDD       	         :typeStr = "covdbBDD"; break;
		case covdbError     	         :typeStr = "covdbError"; break;
		case covdbTable     	         :typeStr = "covdbTable"; break;
		case covdbValueSet      	     :typeStr = "covdbValueSet"; break;
		case covdbSBNRange      	     :typeStr = "covdbSBNRange"; break;
		case covdbTestInfo      	     :typeStr = "covdbTestInfo"; break;
		case covdbUnionMergedDesign      :typeStr = "covdbUnionMergedDesign"; break;
		case covdbLastObjEntry      	 :typeStr = "covdbLastObjEntry"; break;
		default :typeStr="unkown type";break;
	}
	return typeStr;
}
void printCoverageParams(CoverageParams params){
    printf("CoverageExtractToolServer: input %s, %s, %s, %d, %d\n",
           params.vdbName, params.testName, params.targetModuleName,
           params.startLineNo, params.endLineNo);
    printf("\tcoverage database is : %s\n", params.vdbName);
    printf("\ttest name is : %s\n", params.testName);
    printf("\tcheck module is : %s\n", params.targetModuleName);
    printf("\tstart line number is : %d\n", params.startLineNo);
    printf("\tend line number is : %d\n", params.endLineNo);
}
int main(int argc, char* argv[]) {
    char input[1024];
    char output[1024 * 1024]; // 1MB output buffer
    
    printf("CoverageExtractToolServer: ready for queries\n");
    printf("CoverageExtractToolServer: format: <vdbPath> <testPath> <moduleName> <start-end>\n");
    printf("CoverageExtractToolServer: type 'exit' to quit\n");
    printf("QUERY_END\n");
    fflush(stdout);
    
    while (1) {
        // 读取输入
        if (fgets(input, sizeof(input), stdin) == NULL) {
            printf("{\"error\":\"EOF received\"}\n");
            printf("QUERY_END\n");
            fflush(stdout);
            break;
        }
        
        // 去除末尾换行符
        input[strcspn(input, "\n")] = 0;
        
        // 检查退出命令
        if (strcmp(input, "exit") == 0 || strcmp(input, "quit") == 0) {
            printf("{\"status\":\"exiting\"}\n");
            printf("QUERY_END\n");
            fflush(stdout);
            break;
        }
        
        // 跳过空行
        if (strlen(input) == 0) {
            continue;
        }
        
        // 解析命令
        CoverageParams params = {0};
        if (parseCommand(input, &params) != 0) {
            printf("{\"error\":\"Invalid command format. Expected: <vdbPath> <testPath> <moduleName> <start-end>\"}\n");
            printf("QUERY_END\n");
            fflush(stdout);
            continue;
        }
        
        printf("CoverageExtractToolServer: processing query for module=%s, lines=%d-%d\n", 
               params.targetModuleName, params.startLineNo, params.endLineNo);
        
        // 检查是否需要切换 VDB
        int needSwitchVdb = 0;
        if (!g_state.initialized || strcmp(g_state.currentVdb, params.vdbName) != 0) {
            needSwitchVdb = 1;
        }
        
        // 检查是否需要切换 Test
        int needSwitchTest = 0;
        if (g_state.initialized && strcmp(g_state.currentTest, params.testName) != 0) {
            needSwitchTest = 1;
        }
        
        // 加载/切换 VDB 和 Test
        if (needSwitchVdb) {
            if (service_switch_vdb(params.vdbName, params.testName) != 0) {
                printf("{\"error\":\"Failed to switch VDB\"}\n");
                printf("QUERY_END\n");
                fflush(stdout);
                freeCommand(&params);
                continue;
            }
        } else if (needSwitchTest) {
            if (service_switch_test(params.testName) != 0) {
                printf("{\"error\":\"Failed to switch test\"}\n");
                printf("QUERY_END\n");
                fflush(stdout);
                freeCommand(&params);
                continue;
            }
        }
        
        // 执行查询
        if (service_query(params.targetModuleName, params.startLineNo, params.endLineNo, output, sizeof(output),params) == 0) {
            if (output[0] != '\0') {
                printf("%s\n", output);
            }
        } else {
            if (output[0] != '\0') {
                printf("%s\n", output);
            } else {
                printf("{\"error\":\"Query failed\"}\n");
            }
        }
        
        printf("QUERY_END\n");
        fflush(stdout);
        
        freeCommand(&params);
    }
    
    // 清理
    service_cleanup();
    printf("CoverageExtractToolServer: shutdown complete\n");
    return 0;
}
