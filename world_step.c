/* 暂停世界时间；短按单步，长按按原生子步间隔连续推进。 */
typedef unsigned int U32;
typedef unsigned short U16;
typedef unsigned long long U64;
extern void *iat_module, *iat_proc, *iat_pid, *iat_key;
extern float native_step;
typedef void *(*Module)(const U16 *);
typedef void *(*Proc)(void *, const char *);
typedef U32 (*Pid)(void);
typedef short (*Key)(int);
typedef void *(*Foreground)(void);
typedef U32 (*WindowPid)(void *, U32 *);

struct Settings {
    U32 pause_key, step_key, paused, pause_held, step_held, focused;
    U64 frames, steps;
    float repeat_elapsed;
    U32 repeat_armed;
} world_settings = {78, 77, 0, 0, 0, 0, 0, 0, 0, 0};
static Foreground foreground;
static WindowPid window_pid;

float world_filter(float delta) {
    ++world_settings.frames;
    if (!foreground || !window_pid) {
        static const U16 user32[] = {'u','s','e','r','3','2','.','d','l','l',0};
        void *module = ((Module)iat_module)(user32);
        if (module) {
            foreground = (Foreground)((Proc)iat_proc)(module, "GetForegroundWindow");
            window_pid = (WindowPid)((Proc)iat_proc)(module, "GetWindowThreadProcessId");
        }
    }
    U32 pid = 0;
    U32 pause = (((Key)iat_key)((int)world_settings.pause_key) & 0x8000) != 0;
    U32 step = (((Key)iat_key)((int)world_settings.step_key) & 0x8000) != 0;
    if (foreground && window_pid) window_pid(foreground(), &pid);
    U32 focused = foreground && window_pid && pid == ((Pid)iat_pid)();
    U32 pause_edge = focused && world_settings.focused && pause && !world_settings.pause_held;
    U32 step_edge = focused && world_settings.focused && step && !world_settings.step_held;
    world_settings.pause_held = pause;
    world_settings.step_held = step;
    world_settings.focused = focused;
    if (pause_edge) world_settings.paused ^= 1;
    if (!focused || !step) {
        world_settings.repeat_armed = 0;
        world_settings.repeat_elapsed = 0;
    }
    if (step_edge) {
        world_settings.repeat_armed = 1;
        world_settings.repeat_elapsed = 0;
    }
    /* 持续按住时也保持暂停；切回游戏仍按着的键必须松开重按。 */
    if (world_settings.repeat_armed && step) {
        world_settings.paused = 1;
        if (delta > 0 && native_step > 0 && native_step <= 0.15f) {
            U32 advance = step_edge;
            if (!advance) {
                world_settings.repeat_elapsed += delta;
                /* 第一次连步等满99毫秒，之后按原生33毫秒间隔。 */
                float interval = world_settings.repeat_armed == 1 ? 0.099f : native_step;
                if (world_settings.repeat_elapsed >= interval) {
                    advance = 1;
                    world_settings.repeat_elapsed -= interval;
                    world_settings.repeat_armed = 2;
                    /* 每帧最多一刻；丢弃低帧率造成的整刻积压。 */
                    if (world_settings.repeat_elapsed >= native_step)
                        world_settings.repeat_elapsed = 0;
                }
            }
            if (advance) {
                ++world_settings.steps;
                return native_step;
            }
        } else {
            world_settings.repeat_elapsed = 0;
            world_settings.repeat_armed = 1;
        }
    }
    return world_settings.paused ? 0.0f : delta;
}
