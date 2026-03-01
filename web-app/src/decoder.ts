import pako from 'pako';
import { DecodeResult, ParsedCharacter } from './types';

// === Constants ===
const BASE91_ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!#$%&()*+,./:;<=>?@[]^_`{|}~"';
const DECODE_TABLE: Record<string, number> = {};
for (let i = 0; i < BASE91_ALPHABET.length; i++) {
    DECODE_TABLE[BASE91_ALPHABET[i]] = i;
}

const POSITIONS = ['master', 'assist1', 'assist2'];

const MARK_PRIORITY_MAP: Record<number, number> = {
    1: 5,  // 필수 (Essential)
    3: 4,  // 다다익선 (Recommended)
    4: 3,  // 명함 필수
    0: 2,  // 명함만 (Minimum)
    2: 1   // 후순위 (Low)
};

const LEGACY_V2_CHAR_IDS = [
    103, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120,
    123, 125, 126, 127, 129, 130, 132, 133, 134, 135, 136, 141, 142, 143, 144, 145,
    147, 149, 150, 155, 156, 158, 159
];

const LEGACY_V2_POT_IDS = [
    510301, 510302, 510303, 510304, 510305, 510306, 510307, 510308, 510309, 510310, 510311, 510312, 510313, 510321, 510322, 510323, 510324, 510325, 510326, 510327, 510328, 510329, 510330, 510331, 510332, 510333, 510341, 510342, 510343,
    510701, 510702, 510703, 510704, 510705, 510706, 510707, 510708, 510709, 510710, 510711, 510712, 510713, 510721, 510722, 510723, 510724, 510725, 510726, 510727, 510728, 510729, 510730, 510731, 510732, 510733, 510741, 510742, 510743,
    510801, 510802, 510803, 510804, 510805, 510806, 510807, 510808, 510809, 510810, 510811, 510812, 510813, 510821, 510822, 510823, 510824, 510825, 510826, 510827, 510828, 510829, 510830, 510831, 510832, 510833, 510841, 510842, 510843,
    511001, 511002, 511003, 511004, 511005, 511006, 511007, 511008, 511009, 511010, 511011, 511012, 511013, 511021, 511022, 511023, 511024, 511025, 511026, 511027, 511028, 511029, 511030, 511031, 511032, 511033, 511041, 511042, 511043,
    511101, 511102, 511103, 511104, 511105, 511106, 511107, 511108, 511109, 511110, 511111, 511112, 511113, 511121, 511122, 511123, 511124, 511125, 511126, 511127, 511128, 511129, 511130, 511131, 511132, 511133, 511141, 511142, 511143,
    511201, 511202, 511203, 511204, 511205, 511206, 511207, 511208, 511209, 511210, 511211, 511212, 511213, 511221, 511222, 511223, 511224, 511225, 511226, 511227, 511228, 511229, 511230, 511231, 511232, 511233, 511241, 511242, 511243,
    511301, 511302, 511303, 511304, 511305, 511306, 511307, 511308, 511309, 511310, 511311, 511312, 511313, 511321, 511322, 511323, 511324, 511325, 511326, 511327, 511328, 511329, 511330, 511331, 511332, 511333, 511341, 511342, 511343,
    511401, 511402, 511403, 511404, 511405, 511406, 511407, 511408, 511409, 511410, 511411, 511412, 511413, 511421, 511422, 511423, 511424, 511425, 511426, 511427, 511428, 511429, 511430, 511431, 511432, 511433, 511441, 511442, 511443,
    511501, 511502, 511503, 511504, 511505, 511506, 511507, 511508, 511509, 511510, 511511, 511512, 511513, 511521, 511522, 511523, 511524, 511525, 511526, 511527, 511528, 511529, 511530, 511531, 511532, 511533, 511541, 511542, 511543,
    511601, 511602, 511603, 511604, 511605, 511606, 511607, 511608, 511609, 511610, 511611, 511612, 511613, 511621, 511622, 511623, 511624, 511625, 511626, 511627, 511628, 511629, 511630, 511631, 511632, 511633, 511641, 511642, 511643,
    511701, 511702, 511703, 511704, 511705, 511706, 511707, 511708, 511709, 511710, 511711, 511712, 511713, 511721, 511722, 511723, 511724, 511725, 511726, 511727, 511728, 511729, 511730, 511731, 511732, 511733, 511741, 511742, 511743,
    511801, 511802, 511803, 511804, 511805, 511806, 511807, 511808, 511809, 511810, 511811, 511812, 511813, 511821, 511822, 511823, 511824, 511825, 511826, 511827, 511828, 511829, 511830, 511831, 511832, 511833, 511841, 511842, 511843,
    511901, 511902, 511903, 511904, 511905, 511906, 511907, 511908, 511909, 511910, 511911, 511912, 511913, 511921, 511922, 511923, 511924, 511925, 511926, 511927, 511928, 511929, 511930, 511931, 511932, 511933, 511941, 511942, 511943,
    512001, 512002, 512003, 512004, 512005, 512006, 512007, 512008, 512009, 512010, 512011, 512012, 512013, 512021, 512022, 512023, 512024, 512025, 512026, 512027, 512028, 512029, 512030, 512031, 512032, 512033, 512041, 512042, 512043,
    512301, 512302, 512303, 512304, 512305, 512306, 512307, 512308, 512309, 512310, 512311, 512312, 512313, 512321, 512322, 512323, 512324, 512325, 512326, 512327, 512328, 512329, 512330, 512331, 512332, 512333, 512341, 512342, 512343,
    512501, 512502, 512503, 512504, 512505, 512506, 512507, 512508, 512509, 512510, 512511, 512512, 512513, 512521, 512522, 512523, 512524, 512525, 512526, 512527, 512528, 512529, 512530, 512531, 512532, 512533, 512541, 512542, 512543,
    512601, 512602, 512603, 512604, 512605, 512606, 512607, 512608, 512609, 512610, 512611, 512612, 512613, 512621, 512622, 512623, 512624, 512625, 512626, 512627, 512628, 512629, 512630, 512631, 512632, 512633, 512641, 512642, 512643,
    512701, 512702, 512703, 512704, 512705, 512706, 512707, 512708, 512709, 512710, 512711, 512712, 512713, 512721, 512722, 512723, 512724, 512725, 512726, 512727, 512728, 512729, 512730, 512731, 512732, 512733, 512741, 512742, 512743,
    513001, 513002, 513003, 513004, 513005, 513006, 513007, 513008, 513009, 513010, 513011, 513012, 513013, 513021, 513022, 513023, 513024, 513025, 513026, 513027, 513028, 513029, 513030, 513031, 513032, 513033, 513041, 513042, 513043,
    513201, 513202, 513203, 513204, 513205, 513206, 513207, 513208, 513209, 513210, 513211, 513212, 513213, 513221, 513222, 513223, 513224, 513225, 513226, 513227, 513228, 513229, 513230, 513231, 513232, 513233, 513241, 513242, 513243,
    513301, 513302, 513303, 513304, 513305, 513306, 513307, 513308, 513309, 513310, 513311, 513312, 513313, 513321, 513322, 513323, 513324, 513325, 513326, 513327, 513328, 513329, 513330, 513331, 513332, 513333, 513341, 513342, 513343,
    513401, 513402, 513403, 513404, 513405, 513406, 513407, 513408, 513409, 513410, 513411, 513412, 513413, 513421, 513422, 513423, 513424, 513425, 513426, 513427, 513428, 513429, 513430, 513431, 513432, 513433, 513441, 513442, 513443,
    513501, 513502, 513503, 513504, 513505, 513506, 513507, 513508, 513509, 513510, 513511, 513512, 513513, 513521, 513522, 513523, 513524, 513525, 513526, 513527, 513528, 513529, 513530, 513531, 513532, 513533, 513541, 513542, 513543,
    513601, 513602, 513603, 513604, 513605, 513606, 513607, 513608, 513609, 513610, 513611, 513612, 513613, 513621, 513622, 513623, 513624, 513625, 513626, 513627, 513628, 513629, 513630, 513631, 513632, 513633, 513641, 513642, 513643,
    514101, 514102, 514103, 514104, 514105, 514106, 514107, 514108, 514109, 514110, 514111, 514112, 514113, 514121, 514122, 514123, 514124, 514125, 514126, 514127, 514128, 514129, 514130, 514131, 514132, 514133, 514141, 514142, 514143,
    514201, 514202, 514203, 514204, 514205, 514206, 514207, 514208, 514209, 514210, 514211, 514212, 514213, 514221, 514222, 514223, 514224, 514225, 514226, 514227, 514228, 514229, 514230, 514231, 514232, 514233, 514241, 514242, 514243,
    514301, 514302, 514303, 514304, 514305, 514306, 514307, 514308, 514309, 514310, 514311, 514312, 514313, 514321, 514322, 514323, 514324, 514325, 514326, 514327, 514328, 514329, 514330, 514331, 514332, 514333, 514341, 514342, 514343,
    514401, 514402, 514403, 514404, 514405, 514406, 514407, 514408, 514409, 514410, 514411, 514412, 514413, 514421, 514422, 514423, 514424, 514425, 514426, 514427, 514428, 514429, 514430, 514431, 514432, 514433, 514441, 514442, 514443,
    514501, 514502, 514503, 514504, 514505, 514506, 514507, 514508, 514509, 514510, 514511, 514512, 514513, 514521, 514522, 514523, 514524, 514525, 514526, 514527, 514528, 514529, 514530, 514531, 514532, 514533, 514541, 514542, 514543,
    514701, 514702, 514703, 514704, 514705, 514706, 514707, 514708, 514709, 514710, 514711, 514712, 514713, 514721, 514722, 514723, 514724, 514725, 514726, 514727, 514728, 514729, 514730, 514731, 514732, 514733, 514741, 514742, 514743,
    514901, 514902, 514903, 514904, 514905, 514906, 514907, 514908, 514909, 514910, 514911, 514912, 514913, 514921, 514922, 514923, 514924, 514925, 514926, 514927, 514928, 514929, 514930, 514931, 514932, 514933, 514941, 514942, 514943,
    515001, 515002, 515003, 515004, 515005, 515006, 515007, 515008, 515009, 515010, 515011, 515012, 515013, 515021, 515022, 515023, 515024, 515025, 515026, 515027, 515028, 515029, 515030, 515031, 515032, 515033, 515041, 515042, 515043,
    515501, 515502, 515503, 515504, 515505, 515506, 515507, 515508, 515509, 515510, 515511, 515512, 515513, 515521, 515522, 515523, 515524, 515525, 515526, 515527, 515528, 515529, 515530, 515531, 515532, 515533, 515541, 515542, 515543,
    515601, 515602, 515603, 515604, 515605, 515606, 515607, 515608, 515609, 515610, 515611, 515612, 515613, 515621, 515622, 515623, 515624, 515625, 515626, 515627, 515628, 515629, 515630, 515631, 515632, 515633, 515641, 515642, 515643,
    515801, 515802, 515803, 515804, 515805, 515806, 515807, 515808, 515809, 515810, 515811, 515812, 515813, 515821, 515822, 515823, 515824, 515825, 515826, 515827, 515828, 515829, 515830, 515831, 515832, 515833, 515841, 515842, 515843,
    515901, 515902, 515903, 515904, 515905, 515906, 515907, 515908, 515909, 515910, 515911, 515912, 515913, 515921, 515922, 515923, 515924, 515925, 515926, 515927, 515928, 515929, 515930, 515931, 515932, 515933, 515941, 515942, 515943
];

function decodeBase91(encodedStr: string): Uint8Array {
    let v = -1;
    let b = 0;
    let n = 0;
    const out: number[] = [];

    for (let i = 0; i < encodedStr.length; i++) {
        const char = encodedStr[i];
        if (DECODE_TABLE[char] === undefined) {
            continue;
        }

        const c = DECODE_TABLE[char];

        if (v < 0) {
            v = c;
        } else {
            v += c * 91;
            b |= v << n;
            n += (v & 8191) > 88 ? 13 : 14;

            while (n > 7) {
                out.push(b & 255);
                b >>= 8;
                n -= 8;
            }

            v = -1;
        }
    }

    if (v >= 0) {
        out.push((b | (v << n)) & 255);
    }

    return new Uint8Array(out);
}

function readVarint(data: Uint8Array, offset: number): { result: number, nextOffset: number } {
    let result = 0;
    let shift = 0;
    let pos = offset;

    while (pos < data.length) {
        const byte = data[pos];
        pos += 1;
        result |= (byte & 0x7f) << shift;
        if ((byte & 0x80) === 0) {
            return { result, nextOffset: pos };
        }
        shift += 7;
    }
    throw new Error("Failed to read Varint (reached end of data)");
}

function getMappedId(val: number, isLegacyV2: boolean, legacyList: number[]): number {
    if (!isLegacyV2) {
        return val;
    }
    const idx = val - 1;
    if (idx >= 0 && idx < legacyList.length) {
        return legacyList[idx];
    }
    return val;
}

export function decodeSstoyUrl(url: string): DecodeResult {
    try {
        let urlHash = url;
        if (url.includes('#')) {
            urlHash = url.split('#')[1];
        }

        if (urlHash.includes('build=')) {
            urlHash = urlHash.split('build=')[1];
        }

        urlHash = decodeURIComponent(urlHash);

        let compressedData: Uint8Array | null = null;

        if (urlHash.startsWith('v3d-') || urlHash.startsWith('v2d-')) {
            const payload = urlHash.substring(4);
            const base91Decoded = decodeBase91(payload);

            try {
                // -15 in python corresponds to raw deflate without zlib header
                compressedData = pako.inflateRaw(base91Decoded);
            } catch (e) {
                try {
                    compressedData = pako.inflate(base91Decoded);
                } catch (e2) {
                    return { error: `Decompression failed: ${e2}` };
                }
            }
        } else if (urlHash.startsWith('v3r-') || urlHash.startsWith('v2r-')) {
            return { error: "Raw format (v3r/v2r) not supported yet (Requires Base32768)" };
        } else {
            return { error: "Unknown or legacy URL format" };
        }

        if (!compressedData) {
            return { error: "Empty data" };
        }

        let offset = 0;

        const versionRes = readVarint(compressedData, offset);
        const version = versionRes.result;
        offset = versionRes.nextOffset;

        if (version !== 2 && version !== 3) {
            return { error: `Unsupported version: ${version}` };
        }

        const isLegacyV2 = (version === 2);

        const nameLenRes = readVarint(compressedData, offset);
        const nameLen = nameLenRes.result;
        offset = nameLenRes.nextOffset;

        const buildNameBytes = compressedData.slice(offset, offset + nameLen);
        const buildName = new TextDecoder('utf-8').decode(buildNameBytes);
        offset += nameLen;

        const slotMask = compressedData[offset];
        offset += 1;

        const parsedCharacters: Record<string, ParsedCharacter> = {};

        for (let i = 0; i < POSITIONS.length; i++) {
            const posName = POSITIONS[i];
            if ((slotMask & (1 << i)) === 0) {
                continue;
            }

            const charValRes = readVarint(compressedData, offset);
            const charVal = charValRes.result;
            offset = charValRes.nextOffset;

            const charId = getMappedId(charVal, isLegacyV2, LEGACY_V2_CHAR_IDS);

            const potCountRes = readVarint(compressedData, offset);
            const potCount = potCountRes.result;
            offset = potCountRes.nextOffset;

            const potentials: number[] = [];
            for (let j = 0; j < potCount; j++) {
                const potValRes = readVarint(compressedData, offset);
                const potVal = potValRes.result;
                offset = potValRes.nextOffset;

                const realPot = getMappedId(potVal, isLegacyV2, LEGACY_V2_POT_IDS);
                potentials.push(realPot);
            }

            const levelCountRes = readVarint(compressedData, offset);
            const levelCount = levelCountRes.result;
            offset = levelCountRes.nextOffset;

            const potLevels: PotentialLevelMap = {};
            let prevKey = 0;
            for (let j = 0; j < levelCount; j++) {
                const keyDeltaRes = readVarint(compressedData, offset);
                const keyDelta = keyDeltaRes.result;
                offset = keyDeltaRes.nextOffset;

                const valRes = readVarint(compressedData, offset);
                const val = valRes.result;
                offset = valRes.nextOffset;

                const keyRaw = prevKey + keyDelta;
                const realKey = getMappedId(keyRaw, isLegacyV2, LEGACY_V2_POT_IDS);

                potLevels[realKey] = val + 1;
                prevKey = keyRaw;
            }

            const markCountRes = readVarint(compressedData, offset);
            const markCount = markCountRes.result;
            offset = markCountRes.nextOffset;

            const marks: MarkPriorityMap = {};
            let prevMark = 0;
            for (let j = 0; j < markCount; j++) {
                const deltaRes = readVarint(compressedData, offset);
                const delta = deltaRes.result;
                offset = deltaRes.nextOffset;

                const code = compressedData[offset];
                offset += 1;

                const potIdxRaw = prevMark + delta;
                const realKey = getMappedId(potIdxRaw, isLegacyV2, LEGACY_V2_POT_IDS);

                const priority = MARK_PRIORITY_MAP[code] || 0;
                marks[realKey] = priority;
                prevMark = potIdxRaw;
            }

            parsedCharacters[posName] = {
                char_id: charId,
                mapped_char_idx: charId,
                potentials: potentials,
                mapped_potentials: potentials,
                potential_levels: potLevels,
                marks: marks
            };
        }

        return {
            build_name: buildName,
            raw_characters: parsedCharacters,
            version: version
        };

    } catch (error) {
        return { error: String(error) };
    }
}
