package main

import (
	"net/http"
	"os"
	"fmt"
	"log"
	"encoding/json"
	"time"
	"strings"
	"sort"
	"sync"
)



type Record struct {
	CreatedTime time.Time `json:"created_time"`
	ID string `json:"id"`
}

func (r *Record) UnmarshalJSON(data []byte) error {
	var rawStrings map[string]string

	err := json.Unmarshal(data, &rawStrings)
	if err != nil {
		return err
	}

	for k, v := range rawStrings {
		if strings.ToLower(k) == "created_time" {
			parts := strings.Split(v, "+")
			t := fmt.Sprintf("%v+%v:%v", parts[0],
				parts[1][:2], parts[1][2:])
			timestamp, err := time.Parse(time.RFC3339, t)
			if err != nil {
				log.Fatal(err)
				return err
			}
			r.CreatedTime = timestamp
		}
	}
	return nil
}


type Records []Record

func (r Records) Len() int {
	return len(r)
}

func (r Records) Swap(i, j int) {
	r[i], r[j] = r[j], r[i]
}

func (r Records) Less(i, j int) bool {
	return r[i].CreatedTime.Before(r[j].CreatedTime)
}

type Paging struct {
	Previous string `json:"previous,omitempty"`
	Next string `json:"next,omitempty"`
}

type ResponseWithData struct {
	Data  Records `json:"data"`
	Paging Paging `json:"paging"`
}


const photoURL = "https://graph.facebook.com/v2.8/%v/photos?fields=created_time&type=uploaded&limit=100&access_token=%v"
const postsURL = "https://graph.facebook.com/v2.8/%v/posts?fields=created_time&limit=100&access_token=%v"

func request(activitiesURL string, reportChannel chan ReportStruct) *ResponseWithData {
	response, err := http.Get(activitiesURL)

	if err != nil {
		log.Fatal(err)
		reportChannel <- ReportStruct{Timestamp:"", Err:err}
	}

	defer response.Body.Close()
	paging := new(ResponseWithData)
	json.NewDecoder(response.Body).Decode(paging)
	return paging
}


func GetEarliestActivity(activitiesURL string, activityIndex int, reportChannel chan ReportStruct, fallbackURLs []string, wg *sync.WaitGroup, wc *WaitCounter) {
	paging := request(activitiesURL, reportChannel)
	if paging.Paging.Next != "" {
		fallbackURLs = append(fallbackURLs, paging.Paging.Next)
		wg.Add(1)
		wc.Add(1)
		go func() {
			GetEarliestActivity(paging.Paging.Next, activityIndex,
				reportChannel, fallbackURLs, wg, wc)
		}()
	} else {
		if paging.Data.Len() == 0 {
			beforeLast := fallbackURLs[len(fallbackURLs)-2:len(fallbackURLs)-1]
			paging = request(beforeLast[0], reportChannel)
		}
		sort.Sort(paging.Data)
		for i := 0; i < wc.Count; i++ {
			wg.Done()
		}
		reportChannel <- ReportStruct{Timestamp:paging.Data[activityIndex].CreatedTime.String(), Err:nil}
	}
}

type ReportStruct struct {
	Timestamp string `json:"timestamp"`
	Err error `json:"error"`
}

type IncomeData struct {
	FAPIKEY string `json:"fapikey"`
	UserID string `json:"user_id"`
	ActivityType string `json:"activity_type"`
}


func getEarliestPostDate(data *IncomeData, wg *sync.WaitGroup, wc *WaitCounter) chan ReportStruct {
	reportChan := make(chan ReportStruct)
	fallbackURLs := []string{}
	GetEarliestActivity(fmt.Sprintf(postsURL, data.UserID, data.FAPIKEY), 1, reportChan, fallbackURLs, wg, wc)
	return reportChan
}

func getEarliestPhotoDate(data *IncomeData, wg *sync.WaitGroup, wc *WaitCounter) chan ReportStruct {
	reportChan := make(chan ReportStruct)
	fallbackURLs := []string{}
	GetEarliestActivity(fmt.Sprintf(photoURL, data.UserID, data.FAPIKEY), 0, reportChan, fallbackURLs, wg, wc)
	return reportChan
}

type APIAction func(data *IncomeData, wg *sync.WaitGroup, wc *WaitCounter) chan ReportStruct


type WaitCounter struct {
	Count int
}

func (wc *WaitCounter) Add (i int) {
	wc.Count++
}


func main() {
	income := new(IncomeData)
	json.NewDecoder(os.Stdin).Decode(income)
	mapping := map[string]APIAction {
		"posts": getEarliestPostDate,
		"photos": getEarliestPhotoDate,
	}
	var wg sync.WaitGroup
	wcounter := WaitCounter{Count:0}
	reportChan := mapping[income.ActivityType](income, &wg, &wcounter)
	wg.Wait()
	select {
		case timestamp := <- reportChan:
			fmt.Println(timestamp.Timestamp)
		default:
			fmt.Println("")
	}
	close(reportChan)
}
